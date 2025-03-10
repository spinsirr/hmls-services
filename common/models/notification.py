from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.sql import func
from ..utils.database import Base
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
import enum

class NotificationType(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"

# SQLAlchemy ORM model
class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String, nullable=False)  # Email or phone number
    notification_type = Column(String, nullable=False)  # email, sms, push
    subject = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    notification_metadata = Column(JSON, nullable=True)  # Additional data like appointment ID
    status = Column(String, default="pending")  # pending, sent, failed
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Pydantic models for API
class NotificationBase(BaseModel):
    recipient: str
    notification_type: NotificationType
    subject: Optional[str] = None
    content: str
    notification_metadata: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationUpdate(BaseModel):
    status: Optional[NotificationStatus] = None
    sent_at: Optional[datetime] = None

class NotificationResponse(NotificationBase):
    id: int
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class NotificationBatch(BaseModel):
    notifications: List[NotificationCreate] 