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
import grpc
import grpc.aio
from concurrent import futures
from common.proto import notification_pb2, notification_pb2_grpc

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities and models
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, close_redis, init_db
from common.utils import get_db_session, get_cached_data, set_cached_data, clear_cached_data
from common.utils import AuthGrpcClient
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
    GRPC_PORT: int = 50053

settings = get_settings(NotificationServiceSettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("notification-service")

# Initialize clients
auth_client = AuthGrpcClient()

# Initialize queue
notification_queue = NotificationQueue()

# Initialize resources
async def init_resources():
    await init_redis()
    await init_db()
    # Start notification worker in background
    worker_task = asyncio.create_task(notification_worker())
    logger.info(f"{settings.SERVICE_NAME} started")
    return worker_task

# Cleanup resources
async def cleanup_resources():
    await close_redis()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# Helper function to validate token for gRPC
async def validate_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate a token using the gRPC auth service"""
    try:
        # Get user from token
        user_response = auth_client.get_current_user(token=token)
        
        # Convert to dict
        return {
            "valid": True,
            "user_id": user_response.id,
            "email": user_response.email,
            "is_admin": user_response.is_admin
        }
    except Exception as e:
        logger.error(f"Token validation error: {str(e)}")
        return None

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

# gRPC Service Implementation
class NotificationServiceServicer(notification_pb2_grpc.NotificationServiceServicer):
    async def SendNotification(self, request, context):
        try:
            # Validate token
            token = request.token
            user_data = await validate_token(token)
            if not user_data:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid authentication token")
                return notification_pb2.NotificationResponse()
            
            # Check if user is admin
            if not user_data.get("is_admin", False):
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Only admins can send notifications")
                return notification_pb2.NotificationResponse()
            
            # Create notification data
            notification_data = {
                "recipient": request.recipient,
                "notification_type": request.notification_type,
                "subject": request.subject,
                "content": request.content,
                "notification_metadata": dict(request.notification_metadata),
                "status": "pending"
            }
            
            # Add to queue
            await notification_queue.add(notification_data)
            
            # Create notification in database
            async with get_db_session() as db:
                new_notification = Notification(
                    recipient=request.recipient,
                    notification_type=request.notification_type,
                    subject=request.subject,
                    content=request.content,
                    notification_metadata=dict(request.notification_metadata),
                    status="pending"
                )
                
                db.add(new_notification)
                await db.commit()
                await db.refresh(new_notification)
                
                # Convert to response
                return notification_pb2.NotificationResponse(
                    id=new_notification.id,
                    recipient=new_notification.recipient,
                    notification_type=new_notification.notification_type,
                    subject=new_notification.subject,
                    content=new_notification.content,
                    notification_metadata=new_notification.notification_metadata,
                    status=new_notification.status,
                    created_at=new_notification.created_at.isoformat(),
                    updated_at=new_notification.updated_at.isoformat() if new_notification.updated_at else ""
                )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return notification_pb2.NotificationResponse()
    
    async def GetNotifications(self, request, context):
        try:
            # Validate token
            token = request.token
            user_data = await validate_token(token)
            if not user_data:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details("Invalid authentication token")
                return notification_pb2.NotificationsResponse()
            
            # Check if user is admin
            if not user_data.get("is_admin", False):
                context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                context.set_details("Only admins can view all notifications")
                return notification_pb2.NotificationsResponse()
            
            # Get notifications from database
            async with get_db_session() as db:
                stmt = select(Notification).order_by(Notification.created_at.desc())
                result = await db.execute(stmt)
                notifications = result.scalars().all()
                
                # Convert to response
                notification_responses = []
                for notification in notifications:
                    notification_responses.append(notification_pb2.NotificationResponse(
                        id=notification.id,
                        recipient=notification.recipient,
                        notification_type=notification.notification_type,
                        subject=notification.subject,
                        content=notification.content,
                        notification_metadata=notification.notification_metadata,
                        status=notification.status,
                        created_at=notification.created_at.isoformat(),
                        updated_at=notification.updated_at.isoformat() if notification.updated_at else ""
                    ))
                
                return notification_pb2.NotificationsResponse(
                    notifications=notification_responses
                )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return notification_pb2.NotificationsResponse()
            
    async def HealthCheck(self, request, context):
        try:
            return notification_pb2.HealthCheckResponse(
                status="healthy",
                service=settings.SERVICE_NAME
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Health check error: {str(e)}")
            return notification_pb2.HealthCheckResponse(
                status="unhealthy",
                service=settings.SERVICE_NAME
            )

# Start gRPC server
async def serve_grpc():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    notification_pb2_grpc.add_NotificationServiceServicer_to_server(NotificationServiceServicer(), server)
    listen_addr = f'[::]:{settings.GRPC_PORT}'
    server.add_insecure_port(listen_addr)
    logger.info(f"Starting gRPC server on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

# Main entry point
async def main():
    try:
        worker_task = await init_resources()
        await serve_grpc()
    except asyncio.CancelledError:
        logger.info("Notification worker cancelled")
    finally:
        await cleanup_resources()

if __name__ == "__main__":
    asyncio.run(main()) 