from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import httpx
import os
import sys
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, redis_client, close_redis
from common.utils import AuthGrpcClient, AppointmentGrpcClient, NotificationGrpcClient

# Configure settings
class ApiGatewaySettings(BaseServiceSettings):
    SERVICE_NAME: str = "api-gateway"

settings = get_settings(ApiGatewaySettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

# Initialize clients
auth_client = AuthGrpcClient()
appointment_client = AppointmentGrpcClient()
notification_client = NotificationGrpcClient()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis
    await init_redis()
    logger.info(f"{settings.SERVICE_NAME} started")
    yield
    # Shutdown: Close Redis connection and gRPC clients
    await close_redis()
    auth_client.close()
    appointment_client.close()
    notification_client.close()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# Create FastAPI app
app = FastAPI(
    title="HMLS API Gateway",
    description="API Gateway for HMLS Distributed Services",
    version=settings.SERVICE_VERSION,
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to extract token from request
def get_token_from_header(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header.replace("Bearer ", "")
    return ""

# Health check endpoint
@app.get("/health")
async def health_check():
    # Check if all required services are healthy
    try:
        auth_health = auth_client.health_check()
        appointment_health = appointment_client.health_check()
        notification_health = notification_client.health_check()
        
        all_healthy = (
            auth_health.status == "healthy" and
            appointment_health.status == "healthy" and
            notification_health.status == "healthy"
        )
        
        services_status = {
            "auth_service": auth_health.status,
            "appointment_service": appointment_health.status,
            "notification_service": notification_health.status,
        }
        
        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
        
        return {
            "status": "healthy" if all_healthy else "unhealthy",
            "service": settings.SERVICE_NAME,
            "services": services_status
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": settings.SERVICE_NAME,
                "error": str(e)
            }
        )

# Auth service routes
@app.post("/auth/register")
async def register(request: Request):
    data = await request.json()
    try:
        response = auth_client.register(
            email=data.get("email", ""),
            password=data.get("password", ""),
            full_name=data.get("full_name", "")
        )
        return {
            "id": response.id,
            "email": response.email,
            "full_name": response.full_name,
            "is_active": response.is_active,
            "is_admin": response.is_admin,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Register error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/auth/login")
async def login(request: Request):
    try:
        form_data = await request.form()
        username = form_data.get("username", "")
        password = form_data.get("password", "")
        
        response = auth_client.login(username=username, password=password)
        
        return {
            "access_token": response.access_token,
            "token_type": response.token_type
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/auth/me")
async def get_current_user(request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        response = auth_client.get_current_user(token=token)
        return {
            "id": response.id,
            "email": response.email,
            "full_name": response.full_name,
            "is_active": response.is_active,
            "is_admin": response.is_admin,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Get current user error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

# Appointment service routes
@app.post("/appointments")
async def create_appointment(request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    data = await request.json()
    try:
        response = appointment_client.create_appointment(token=token, data=data)
        return {
            "id": response.id,
            "email": response.email,
            "phone_number": response.phone_number,
            "appointment_time": response.appointment_time,
            "vehicle_year": response.vehicle_year,
            "vehicle_make": response.vehicle_make,
            "vehicle_model": response.vehicle_model,
            "problem_description": response.problem_description,
            "status": response.status,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Create appointment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create appointment: {str(e)}")

@app.get("/appointments")
async def get_appointments(request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        response = appointment_client.get_appointments(token=token)
        return [
            {
                "id": appointment.id,
                "email": appointment.email,
                "phone_number": appointment.phone_number,
                "appointment_time": appointment.appointment_time,
                "vehicle_year": appointment.vehicle_year,
                "vehicle_make": appointment.vehicle_make,
                "vehicle_model": appointment.vehicle_model,
                "problem_description": appointment.problem_description,
                "status": appointment.status,
                "created_at": appointment.created_at,
                "updated_at": appointment.updated_at
            }
            for appointment in response.appointments
        ]
    except Exception as e:
        logger.error(f"Get appointments error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get appointments: {str(e)}")

@app.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: int, request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        response = appointment_client.get_appointment(token=token, appointment_id=appointment_id)
        return {
            "id": response.id,
            "email": response.email,
            "phone_number": response.phone_number,
            "appointment_time": response.appointment_time,
            "vehicle_year": response.vehicle_year,
            "vehicle_make": response.vehicle_make,
            "vehicle_model": response.vehicle_model,
            "problem_description": response.problem_description,
            "status": response.status,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Get appointment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get appointment: {str(e)}")

@app.put("/appointments/{appointment_id}")
async def update_appointment(appointment_id: int, request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    data = await request.json()
    try:
        response = appointment_client.update_appointment(token=token, appointment_id=appointment_id, data=data)
        return {
            "id": response.id,
            "email": response.email,
            "phone_number": response.phone_number,
            "appointment_time": response.appointment_time,
            "vehicle_year": response.vehicle_year,
            "vehicle_make": response.vehicle_make,
            "vehicle_model": response.vehicle_model,
            "problem_description": response.problem_description,
            "status": response.status,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Update appointment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to update appointment: {str(e)}")

@app.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: int, request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        response = appointment_client.delete_appointment(token=token, appointment_id=appointment_id)
        return {
            "success": response.success,
            "message": response.message
        }
    except Exception as e:
        logger.error(f"Delete appointment error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete appointment: {str(e)}")

# Notification service routes (admin only)
@app.post("/notifications")
async def send_notification(request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    data = await request.json()
    try:
        response = notification_client.send_notification(token=token, data=data)
        return {
            "id": response.id,
            "recipient": response.recipient,
            "notification_type": response.notification_type,
            "subject": response.subject,
            "content": response.content,
            "notification_metadata": dict(response.notification_metadata),
            "status": response.status,
            "created_at": response.created_at,
            "updated_at": response.updated_at
        }
    except Exception as e:
        logger.error(f"Send notification error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")

@app.get("/notifications")
async def get_notifications(request: Request):
    token = get_token_from_header(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        response = notification_client.get_notifications(token=token)
        return [
            {
                "id": notification.id,
                "recipient": notification.recipient,
                "notification_type": notification.notification_type,
                "subject": notification.subject,
                "content": notification.content,
                "notification_metadata": dict(notification.notification_metadata),
                "status": notification.status,
                "created_at": notification.created_at,
                "updated_at": notification.updated_at
            }
            for notification in response.notifications
        ]
    except Exception as e:
        logger.error(f"Get notifications error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get notifications: {str(e)}")

# Error handling
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 