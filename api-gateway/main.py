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
from common.utils import AuthServiceClient, AppointmentServiceClient, NotificationServiceClient

# Configure settings
class ApiGatewaySettings(BaseServiceSettings):
    SERVICE_NAME: str = "api-gateway"

settings = get_settings(ApiGatewaySettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api-gateway")

# Initialize clients
auth_client = AuthServiceClient()
appointment_client = AppointmentServiceClient()
notification_client = NotificationServiceClient()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis
    await init_redis()
    logger.info(f"{settings.SERVICE_NAME} started")
    yield
    # Shutdown: Close Redis connection
    await close_redis()
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

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": settings.SERVICE_NAME}

# Auth service routes
@app.post("/auth/register")
async def register(request: Request):
    data = await request.json()
    return await auth_client.post("register", data=data)

@app.post("/auth/login")
async def login(request: Request):
    try:
        # Get the raw body content and forward it directly
        body = await request.body()
        
        # Use httpx directly for more control
        async with httpx.AsyncClient() as client:
            auth_response = await client.post(
                f"{auth_client.base_url}/login",
                content=body,
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            
            # Return the response directly
            return JSONResponse(
                content=auth_response.json(),
                status_code=auth_response.status_code
            )
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")

@app.get("/auth/me")
async def get_current_user(request: Request):
    # Forward the authorization header
    headers = {"Authorization": request.headers.get("Authorization")}
    return await auth_client.get("me", headers=headers)

# Appointment service routes
@app.post("/appointments")
async def create_appointment(request: Request):
    data = await request.json()
    headers = {"Authorization": request.headers.get("Authorization")}
    return await appointment_client.post("", data=data, headers=headers)

@app.get("/appointments")
async def get_appointments(request: Request):
    headers = {"Authorization": request.headers.get("Authorization")}
    return await appointment_client.get("", headers=headers)

@app.get("/appointments/{appointment_id}")
async def get_appointment(appointment_id: int, request: Request):
    headers = {"Authorization": request.headers.get("Authorization")}
    return await appointment_client.get(f"{appointment_id}", headers=headers)

@app.put("/appointments/{appointment_id}")
async def update_appointment(appointment_id: int, request: Request):
    data = await request.json()
    headers = {"Authorization": request.headers.get("Authorization")}
    return await appointment_client.put(f"{appointment_id}", data=data, headers=headers)

@app.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: int, request: Request):
    headers = {"Authorization": request.headers.get("Authorization")}
    return await appointment_client.delete(f"{appointment_id}", headers=headers)

# Notification service routes (admin only)
@app.post("/notifications")
async def send_notification(request: Request):
    data = await request.json()
    headers = {"Authorization": request.headers.get("Authorization")}
    return await notification_client.post("", data=data, headers=headers)

@app.get("/notifications")
async def get_notifications(request: Request):
    headers = {"Authorization": request.headers.get("Authorization")}
    return await notification_client.get("", headers=headers)

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