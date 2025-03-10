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
from datetime import datetime, timedelta
import pytz
import asyncio
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities and models
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, close_redis, init_db
from common.utils import get_db_session, get_cached_data, set_cached_data, clear_cached_data
from common.utils import AuthServiceClient, NotificationServiceClient
from common.utils import AppointmentQueue
from common.models import Appointment, AppointmentCreate, AppointmentUpdate, AppointmentResponse, AppointmentQueueResponse
from common.models import NotificationCreate, NotificationType

# Configure settings
class AppointmentServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "appointment-service"

settings = get_settings(AppointmentServiceSettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("appointment-service")

# Initialize clients
auth_client = AuthServiceClient()
notification_client = NotificationServiceClient()

# Initialize queue
appointment_queue = AppointmentQueue()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis, database, and worker
    await init_redis()
    await init_db()
    # Start appointment worker in background
    worker_task = asyncio.create_task(appointment_worker())
    logger.info(f"{settings.SERVICE_NAME} started")
    yield
    # Shutdown: Cancel worker and close Redis connection
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        logger.info("Appointment worker cancelled")
    await close_redis()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# Create FastAPI app
app = FastAPI(
    title="HMLS Appointment Service",
    description="Appointment Management Service for HMLS",
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

# Check if appointment time is available
async def is_time_slot_available(db: AsyncSession, appointment_time: datetime, exclude_id: int = None) -> bool:
    """Check if the appointment time slot is available"""
    try:
        # Convert to UTC for consistent comparison
        if appointment_time.tzinfo is None:
            appointment_time = pytz.UTC.localize(appointment_time)
            
        # Define time window (1 hour slots)
        start_time = appointment_time - timedelta(minutes=30)
        end_time = appointment_time + timedelta(minutes=30)
        
        # Query for overlapping appointments
        query = select(Appointment).where(
            and_(
                Appointment.appointment_time >= start_time,
                Appointment.appointment_time <= end_time,
                Appointment.status != "cancelled"
            )
        )
        
        # Exclude current appointment if updating
        if exclude_id:
            query = query.where(Appointment.id != exclude_id)
            
        result = await db.execute(query)
        existing_appointments = result.scalars().all()
        
        return len(existing_appointments) == 0
    except Exception as e:
        logger.error(f"Error checking time slot availability: {e}")
        raise

# Background worker for processing appointment queue
async def appointment_worker():
    """Background worker to process appointment requests from the queue"""
    logger.info("Starting appointment worker")
    
    while True:
        try:
            # Process any failed messages first
            requeued = await appointment_queue.requeue_failed()
            if requeued > 0:
                logger.info(f"Requeued {requeued} failed appointment requests")
            
            # Get next message from queue
            message = await appointment_queue.dequeue()
            if not message:
                # No messages, sleep and try again
                await asyncio.sleep(1)
                continue
                
            logger.info(f"Processing appointment request: {message.get('id')}")
            
            # Process the appointment
            async with get_db_session() as db:
                # Check if appointment exists (for updates)
                appointment_id = message.get("id")
                if appointment_id:
                    stmt = select(Appointment).where(Appointment.id == appointment_id)
                    result = await db.execute(stmt)
                    appointment = result.scalar_one_or_none()
                    
                    if not appointment:
                        logger.error(f"Appointment not found: {appointment_id}")
                        await appointment_queue.complete(message)
                        continue
                        
                    # Update appointment
                    appointment_time = message.get("appointment_time")
                    if isinstance(appointment_time, str):
                        appointment_time = datetime.fromisoformat(appointment_time)
                        
                    # Check if time slot is available
                    if appointment_time and appointment_time != appointment.appointment_time:
                        is_available = await is_time_slot_available(db, appointment_time, appointment.id)
                        if not is_available:
                            logger.error(f"Time slot not available: {appointment_time}")
                            await appointment_queue.complete(message)
                            continue
                            
                        appointment.appointment_time = appointment_time
                        
                    # Update other fields
                    for field in ["email", "phone_number", "vehicle_year", "vehicle_make", 
                                 "vehicle_model", "problem_description", "status"]:
                        if field in message and message[field] is not None:
                            setattr(appointment, field, message[field])
                            
                    await db.commit()
                    
                    # Send notification for update
                    if appointment.status == "confirmed":
                        await send_appointment_notification(
                            appointment.email,
                            "Appointment Confirmed",
                            f"Your appointment on {appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been confirmed.",
                            {"appointment_id": appointment.id}
                        )
                else:
                    # Create new appointment
                    appointment_time = message.get("appointment_time")
                    if isinstance(appointment_time, str):
                        appointment_time = datetime.fromisoformat(appointment_time)
                        
                    # Check if time slot is available
                    is_available = await is_time_slot_available(db, appointment_time)
                    if not is_available:
                        logger.error(f"Time slot not available: {appointment_time}")
                        await appointment_queue.complete(message)
                        continue
                        
                    # Create appointment
                    new_appointment = Appointment(
                        email=message.get("email"),
                        phone_number=message.get("phone_number"),
                        appointment_time=appointment_time,
                        vehicle_year=message.get("vehicle_year"),
                        vehicle_make=message.get("vehicle_make"),
                        vehicle_model=message.get("vehicle_model"),
                        problem_description=message.get("problem_description"),
                        status="pending"
                    )
                    
                    db.add(new_appointment)
                    await db.commit()
                    await db.refresh(new_appointment)
                    
                    # Send notification for new appointment
                    await send_appointment_notification(
                        new_appointment.email,
                        "Appointment Received",
                        f"Your appointment request for {new_appointment.appointment_time.strftime('%Y-%m-%d %H:%M')} has been received and is pending confirmation.",
                        {"appointment_id": new_appointment.id}
                    )
                    
            # Mark message as completed
            await appointment_queue.complete(message)
            
        except Exception as e:
            logger.error(f"Error processing appointment: {e}")
            await asyncio.sleep(1)  # Sleep to avoid tight loop on errors

# Helper function to send notifications
async def send_appointment_notification(recipient: str, subject: str, content: str, metadata: Dict[str, Any] = None):
    """Send a notification about an appointment"""
    try:
        notification = NotificationCreate(
            recipient=recipient,
            notification_type=NotificationType.EMAIL,
            subject=subject,
            content=content,
            notification_metadata=metadata or {}
        )
        
        await notification_client.post("", data=notification.dict())
    except Exception as e:
        logger.error(f"Error sending notification: {e}")

# Create appointment endpoint
@app.post("", response_model=AppointmentQueueResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_appointment(
    appointment: AppointmentCreate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Create a temporary record to get an ID
    temp_appointment = Appointment(
        email=appointment.email,
        phone_number=appointment.phone_number,
        appointment_time=appointment.appointment_time,
        vehicle_year=appointment.vehicle_year,
        vehicle_make=appointment.vehicle_make,
        vehicle_model=appointment.vehicle_model,
        problem_description=appointment.problem_description,
        status="pending"
    )
    
    db.add(temp_appointment)
    await db.commit()
    await db.refresh(temp_appointment)
    
    # Queue the appointment for processing
    appointment_data = {
        "id": temp_appointment.id,
        "email": appointment.email,
        "phone_number": appointment.phone_number,
        "appointment_time": appointment.appointment_time.isoformat(),
        "vehicle_year": appointment.vehicle_year,
        "vehicle_make": appointment.vehicle_make,
        "vehicle_model": appointment.vehicle_model,
        "problem_description": appointment.problem_description
    }
    
    queue_response = await appointment_queue.enqueue(appointment_data)
    
    # Clear cache
    background_tasks.add_task(clear_cached_data, f"appointments:user:{current_user['email']}")
    
    return queue_response

# Get all appointments endpoint
@app.get("", response_model=List[AppointmentResponse])
async def get_appointments(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Try to get from cache
    cache_key = f"appointments:user:{current_user['email']}"
    cached_data = await get_cached_data(cache_key)
    
    if cached_data:
        return cached_data
    
    # Get from database
    stmt = select(Appointment).where(Appointment.email == current_user["email"])
    result = await db.execute(stmt)
    appointments = result.scalars().all()
    
    # Cache the result
    await set_cached_data(cache_key, [appointment.__dict__ for appointment in appointments])
    
    return appointments

# Get appointment by ID endpoint
@app.get("/{appointment_id}", response_model=AppointmentResponse)
async def get_appointment(
    appointment_id: int,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(Appointment).where(
        and_(
            Appointment.id == appointment_id,
            Appointment.email == current_user["email"]
        )
    )
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    return appointment

# Update appointment endpoint
@app.put("/{appointment_id}", response_model=AppointmentQueueResponse)
async def update_appointment(
    appointment_id: int,
    appointment_update: AppointmentUpdate,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Check if appointment exists and belongs to user
    stmt = select(Appointment).where(
        and_(
            Appointment.id == appointment_id,
            Appointment.email == current_user["email"]
        )
    )
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Queue the update for processing
    update_data = {
        "id": appointment_id,
        "email": appointment_update.email,
        "phone_number": appointment_update.phone_number,
        "appointment_time": appointment_update.appointment_time.isoformat() if appointment_update.appointment_time else None,
        "vehicle_year": appointment_update.vehicle_year,
        "vehicle_make": appointment_update.vehicle_make,
        "vehicle_model": appointment_update.vehicle_model,
        "problem_description": appointment_update.problem_description,
        "status": appointment_update.status
    }
    
    # Remove None values
    update_data = {k: v for k, v in update_data.items() if v is not None}
    
    queue_response = await appointment_queue.enqueue(update_data)
    
    # Clear cache
    background_tasks.add_task(clear_cached_data, f"appointments:user:{current_user['email']}")
    
    return queue_response

# Cancel appointment endpoint
@app.delete("/{appointment_id}", response_model=AppointmentQueueResponse)
async def cancel_appointment(
    appointment_id: int,
    background_tasks: BackgroundTasks,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Check if appointment exists and belongs to user
    stmt = select(Appointment).where(
        and_(
            Appointment.id == appointment_id,
            Appointment.email == current_user["email"]
        )
    )
    result = await db.execute(stmt)
    appointment = result.scalar_one_or_none()
    
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found"
        )
    
    # Queue the cancellation for processing
    cancel_data = {
        "id": appointment_id,
        "status": "cancelled"
    }
    
    queue_response = await appointment_queue.enqueue(cancel_data)
    
    # Clear cache
    background_tasks.add_task(clear_cached_data, f"appointments:user:{current_user['email']}")
    
    return queue_response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True) 