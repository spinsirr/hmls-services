from sqlalchemy import select, insert, update, delete, Column, Integer, String, Boolean, DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
import os
import sys
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import asyncio
import grpc
import grpc.aio
from concurrent import futures

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import common utilities and models
from common.utils.config import BaseServiceSettings
from common.utils import get_settings, init_redis, close_redis, init_db
from common.utils import get_db_session, verify_password, get_password_hash, create_access_token, decode_access_token
from common.models import User, UserCreate, UserUpdate, UserResponse, UserBase

# Import gRPC generated code
from common.proto import auth_pb2, auth_pb2_grpc

# Configure settings
class AuthServiceSettings(BaseServiceSettings):
    SERVICE_NAME: str = "auth-service"
    GRPC_PORT: int = 50051

settings = get_settings(AuthServiceSettings)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-service")

# Initialize resources
async def init_resources():
    await init_redis()
    await init_db()
    logger.info(f"{settings.SERVICE_NAME} started")

# Cleanup resources
async def cleanup_resources():
    await close_redis()
    logger.info(f"{settings.SERVICE_NAME} shut down")

# gRPC Service Implementation
class AuthServiceServicer(auth_pb2_grpc.AuthServiceServicer):
    async def Register(self, request, context):
        try:
            async with get_db_session() as db:
                # Check if user already exists
                stmt = select(User).where(User.email == request.email)
                result = await db.execute(stmt)
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    context.set_code(grpc.StatusCode.ALREADY_EXISTS)
                    context.set_details("Email already registered")
                    return auth_pb2.UserResponse()
                    
                # Create new user
                hashed_password = get_password_hash(request.password)
                
                # Split full_name into first_name and last_name
                name_parts = request.full_name.split(' ', 1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""
                
                new_user = User(
                    email=request.email,
                    first_name=first_name,
                    last_name=last_name,
                    phone_number="Not provided",  # Required field, providing default
                    hashed_password=hashed_password,
                    is_active=True
                )
                
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)
                
                # Convert to response
                return auth_pb2.UserResponse(
                    id=new_user.id,
                    email=new_user.email,
                    full_name=f"{new_user.first_name} {new_user.last_name}".strip(),
                    is_active=new_user.is_active,
                    is_admin=getattr(new_user, 'is_admin', False),  # Use getattr in case is_admin doesn't exist
                    created_at=new_user.created_at.isoformat(),
                    updated_at=new_user.updated_at.isoformat() if new_user.updated_at else ""
                )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return auth_pb2.UserResponse()
    
    async def Login(self, request, context):
        try:
            logger.info(f"Login request received for username: {request.username}")
            async with get_db_session() as db:
                # Find user by email
                stmt = select(User).where(User.email == request.username)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user:
                    logger.error(f"User not found: {request.username}")
                    context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                    context.set_details("Incorrect email or password")
                    return auth_pb2.TokenResponse()
                
                # Verify password
                if not verify_password(request.password, user.hashed_password):
                    logger.error(f"Invalid password for user: {request.username}")
                    context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                    context.set_details("Incorrect email or password")
                    return auth_pb2.TokenResponse()
                
                # Create access token
                access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
                access_token = create_access_token(
                    data={"sub": user.email}, expires_delta=access_token_expires
                )
                
                logger.info(f"Login successful for user: {request.username}")
                return auth_pb2.TokenResponse(
                    access_token=access_token,
                    token_type="bearer"
                )
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return auth_pb2.TokenResponse()
    
    async def GetCurrentUser(self, request, context):
        try:
            # Decode token
            try:
                payload = decode_access_token(request.token)
                email = payload.get("sub")
                if email is None:
                    context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                    context.set_details("Invalid authentication credentials")
                    return auth_pb2.UserResponse()
            except Exception as e:
                context.set_code(grpc.StatusCode.UNAUTHENTICATED)
                context.set_details(f"Invalid authentication credentials: {str(e)}")
                return auth_pb2.UserResponse()
                
            # Get user from database
            async with get_db_session() as db:
                # Find user by email
                stmt = select(User).where(User.email == email)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if user is None:
                    context.set_code(grpc.StatusCode.NOT_FOUND)
                    context.set_details("User not found")
                    return auth_pb2.UserResponse()
                
                if not user.is_active:
                    context.set_code(grpc.StatusCode.PERMISSION_DENIED)
                    context.set_details("Inactive user")
                    return auth_pb2.UserResponse()
                
                # Convert to response
                return auth_pb2.UserResponse(
                    id=user.id,
                    email=user.email,
                    full_name=f"{user.first_name} {user.last_name}".strip(),
                    is_active=user.is_active,
                    is_admin=user.is_admin,
                    created_at=user.created_at.isoformat(),
                    updated_at=user.updated_at.isoformat() if user.updated_at else ""
                )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return auth_pb2.UserResponse()
            
    async def HealthCheck(self, request, context):
        try:
            return auth_pb2.HealthCheckResponse(
                status="healthy",
                service=settings.SERVICE_NAME
            )
        except Exception as e:
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Health check error: {str(e)}")
            return auth_pb2.HealthCheckResponse(
                status="unhealthy",
                service=settings.SERVICE_NAME
            )

# Start gRPC server
async def serve_grpc():
    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))
    auth_pb2_grpc.add_AuthServiceServicer_to_server(AuthServiceServicer(), server)
    listen_addr = f'[::]:{settings.GRPC_PORT}'
    server.add_insecure_port(listen_addr)
    logger.info(f"Starting gRPC server on {listen_addr}")
    await server.start()
    await server.wait_for_termination()

# Main entry point
async def main():
    try:
        await init_resources()
        await serve_grpc()
    finally:
        await cleanup_resources()

if __name__ == "__main__":
    asyncio.run(main()) 