from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import IntegrityError
import os
import sys
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities and models
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, close_redis, init_db
from common.utils import get_db_session, verify_password, get_password_hash, create_access_token, decode_access_token
from common.models import User, UserCreate, UserUpdate, UserResponse

# Configure settings
class AuthServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "auth-service"

settings = get_settings(AuthServiceSettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Redis and database
    await init_redis()
    await init_db()
    logger.info(f"{settings.SERVICE_NAME} started")
    yield
    # Shutdown: Close Redis connection
    await close_redis()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# Create FastAPI app
app = FastAPI(
    title="HMLS Auth Service",
    description="Authentication Service for HMLS",
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
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception
        
    email: str = payload.get("sub")
    if email is None:
        raise credentials_exception
        
    async with db as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
        
    return user

# Register endpoint
@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: AsyncSession = Depends(get_db_session)):
    async with db as session:
        # Check if user already exists
        stmt = select(User).where(User.email == user_data.email)
        result = await session.execute(stmt)
        existing_user = result.scalar_one_or_none()
    
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        db_user = User(
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            email=user_data.email,
            phone_number=user_data.phone_number,
            hashed_password=hashed_password,
            vehicle_year=user_data.vehicle_year,
            vehicle_make=user_data.vehicle_make,
            vehicle_model=user_data.vehicle_model,
            vehicle_vin=user_data.vehicle_vin
        )
    
        session.add(db_user)
        try:
            await session.commit()
            await session.refresh(db_user)
            return db_user
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Registration failed"
            )

# Login endpoint
@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db_session)):
    # Find user by email
    async with db as session:
        stmt = select(User).where(User.email == form_data.username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    
        # Verify user and password
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email},
            expires_delta=access_token_expires
        )
    
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user.id,
            "email": user.email
        }

# Get current user endpoint
@app.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

# Update user endpoint
@app.put("/me", response_model=UserResponse)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    # Update user fields
    async with db as session:
        if user_update.first_name:
            current_user.first_name = user_update.first_name
        if user_update.last_name:
            current_user.last_name = user_update.last_name
        if user_update.email:
            # Check if email is already taken
            if user_update.email != current_user.email:
                stmt = select(User).where(User.email == user_update.email)
                result = await session.execute(stmt)
                existing_user = result.scalar_one_or_none()
                if existing_user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Email already registered"
                    )
            current_user.email = user_update.email
        if user_update.phone_number:
            current_user.phone_number = user_update.phone_number
        if user_update.vehicle_year:
            current_user.vehicle_year = user_update.vehicle_year
        if user_update.vehicle_make:
            current_user.vehicle_make = user_update.vehicle_make
        if user_update.vehicle_model:
            current_user.vehicle_model = user_update.vehicle_model
        if user_update.vehicle_vin:
            current_user.vehicle_vin = user_update.vehicle_vin
        if user_update.password:
            current_user.hashed_password = get_password_hash(user_update.password)
    
        try:
            await session.commit()
            await session.refresh(current_user)
            return current_user
        except IntegrityError:
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Update failed"
            )

# Validate token endpoint (for service-to-service communication)
@app.post("/validate-token")
async def validate_token(request: Request, db: AsyncSession = Depends(get_db_session)):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = auth_header.split(" ")[1]
    payload = decode_access_token(token)
    
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    async with db as session:
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
    
        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid user",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
        return {
            "valid": True,
            "user_id": user.id,
            "email": user.email
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 