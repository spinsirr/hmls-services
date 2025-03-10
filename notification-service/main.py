from fastapi import FastAPI, Depends, HTTPException, status, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from sqlalchemy.exc import IntegrityError
import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import pytz
import asyncio
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities and models
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, close_redis, init_db
from common.utils import get_db_session, get_cached_data, set_cached_data, clear_cached_data
from common.utils import AuthServiceClient
from common.utils import NotificationQueue
from common.models import Notification, NotificationCreate, NotificationUpdate, NotificationResponse, NotificationBatch
from common.models import NotificationType, NotificationStatus

# Configure settings
class NotificationServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "notification-service"
    SMTP_SERVER: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "notifications@example.com"
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = "notifications@example.com"
    SMS_API_KEY: str = ""

settings = get_settings(NotificationServiceSettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

# Initialize clients
auth_client = AuthServiceClient()

# Initialize queue
notification_queue = NotificationQueue()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis, database, and worker
    await init_redis()
    await init_db()
    # Start notification worker in background
    worker_task = asyncio.create_task(notification_worker())
    logger.info(f"{settings.SERVICE_NAME} started")
    yield
    # Shutdown: Cancel worker and close Redis connection
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Notification worker cancelled")
    await close_redis()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# Create FastAPI app
app = FastAPI(
    title="HMLS Notification Service",
    description="Notification Service for HMLS",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for service-to-service communication
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}

# Authentication dependency
async def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Validate token with Auth Service
        user_data = await auth_client.post("validate-token", headers={"Authorization": auth_header})
        return user_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Background worker for processing notification queue
async def notification_worker():
    """Background worker to process notification requests from the queue"""
    logger.info("Starting notification worker")
    
    while True:
        try:
            # Process any failed messages first
            requeued = await notification_queue.requeue_failed()
            if requeued > 0:
                logger.info(f"Requeued {requeued} failed notification requests")
            
            # Get next message from queue
            message = await notification_queue.dequeue()
            if not message:
                # No messages, sleep and try again
                await asyncio.sleep(1)
                continue
                
            logger.info(f"Processing notification: {message.get('id')}")
            
            # Process the notification
            async with get_db_session() as db:
                # Check if notification exists (for updates)
                notification_id = message.get("id")
                if notification_id:
                    stmt = select(Notification).where(Notification.id == notification_id)
                    result = await db.execute(stmt)
                    notification = result.scalar_one_or_none()
                    
                    if not notification:
                        logger.error(f"Notification not found: {notification_id}")
                        await notification_queue.complete(message)
                        continue
                        
                    # Update notification
                    for field in ["status", "sent_at"]:
                        if field in message and message[field] is not None:
                            setattr(notification, field, message[field])
                            
                    await db.commit()
                else:
                    # Create new notification
                    new_notification = Notification(
                        recipient=message.get("recipient"),
                        notification_type=message.get("notification_type"),
                        subject=message.get("subject"),
                        content=message.get("content"),
                        notification_metadata=message.get("notification_metadata", {}),
                        status="pending"
                    )
                    
                    db.add(new_notification)
                    await db.commit()
                    await db.refresh(new_notification)
                    
                    # Send the notification
                    success = await send_notification(
                        new_notification.notification_type,
                        new_notification.recipient,
                        new_notification.subject,
                        new_notification.content
                    )
                    
                    # Update status
                    if success:
                        new_notification.status = "sent"
                        new_notification.sent_at = datetime.now(pytz.UTC)
                    else:
                        new_notification.status = "failed"
                        
                    await db.commit()
                    
            # Mark message as completed
            await notification_queue.complete(message)
            
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            await asyncio.sleep(1)  # Sleep to avoid tight loop on errors

# Helper function to send notifications
async def send_notification(notification_type: str, recipient: str, subject: str, content: str) -> bool:
    """Send a notification based on type"""
    try:
        if notification_type == NotificationType.EMAIL:
            return await send_email(recipient, subject, content)
        elif notification_type == NotificationType.SMS:
            return await send_sms(recipient, content)
        else:
            logger.error(f"Unsupported notification type: {notification_type}")
            return False
    except Exception as e:
        logger.error(f"Error sending notification: {e}")
        return False

async def send_email(recipient: str, subject: str, content: str) -> bool:
    """Send an email notification"""
    try:
        # This would be replaced with actual email sending logic
        logger.info(f"Sending email to {recipient}: {subject}")
        
        # For demonstration purposes, we'll just log the email
        # In a real implementation, you would use SMTP or an email service
        if settings.SMTP_PASSWORD:  # Only try to send if configured
            message = MIMEMultipart()
            message["From"] = settings.SMTP_FROM_EMAIL
            message["To"] = recipient
            message["Subject"] = subject
            message.attach(MIMEText(content, "plain"))
            
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(message)
        
        return True
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        return False

async def send_sms(recipient: str, content: str) -> bool:
    """Send an SMS notification"""
    try:
        # This would be replaced with actual SMS sending logic
        logger.info(f"Sending SMS to {recipient}: {content[:20]}...")
        
        # For demonstration purposes, we'll just log the SMS
        # In a real implementation, you would use an SMS service API
        
        return True
    except Exception as e:
        logger.error(f"Error sending SMS: {e}")
        return False

# Create notification endpoint
@app.post("", response_model=NotificationResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_notification(
    notification: NotificationCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Create notification record
    db_notification = Notification(
        recipient=notification.recipient,
        notification_type=notification.notification_type,
        subject=notification.subject,
        content=notification.content,
        notification_metadata=notification.notification_metadata,
        status="pending"
    )
    
    db.add(db_notification)
    await db.commit()
    await db.refresh(db_notification)
    
    # Queue the notification for processing
    notification_data = {
        "id": db_notification.id,
        "recipient": notification.recipient,
        "notification_type": notification.notification_type,
        "subject": notification.subject,
        "content": notification.content,
        "notification_metadata": notification.notification_metadata
    }
    
    await notification_queue.enqueue(notification_data)
    
    return db_notification

# Create batch notifications endpoint
@app.post("/batch", response_model=List[NotificationResponse], status_code=status.HTTP_202_ACCEPTED)
async def create_batch_notifications(
    batch: NotificationBatch,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Create notification records
    db_notifications = []
    
    for notification in batch.notifications:
        db_notification = Notification(
            recipient=notification.recipient,
            notification_type=notification.notification_type,
            subject=notification.subject,
            content=notification.content,
            notification_metadata=notification.notification_metadata,
            status="pending"
        )
        
        db.add(db_notification)
        db_notifications.append(db_notification)
    
    await db.commit()
    
    # Queue the notifications for processing
    for notification in db_notifications:
        await db.refresh(notification)
        
        notification_data = {
            "id": notification.id,
            "recipient": notification.recipient,
            "notification_type": notification.notification_type,
            "subject": notification.subject,
            "content": notification.content,
            "notification_metadata": notification.notification_metadata
        }
        
        await notification_queue.enqueue(notification_data)
    
    return db_notifications

# Get all notifications endpoint
@app.get("", response_model=List[NotificationResponse])
async def get_notifications(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Get all notifications
    stmt = select(Notification)
    result = await db.execute(stmt)
    notifications = result.scalars().all()
    
    return notifications

# Get notification by ID endpoint
@app.get("/{notification_id}", response_model=NotificationResponse)
async def get_notification(
    notification_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Notification).where(Notification.id == notification_id)
    result = await db.execute(stmt)
    notification = result.scalar_one_or_none()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    return notification

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True) 