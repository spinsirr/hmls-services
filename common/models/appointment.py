from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from ..utils.database import Base
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

# SQLAlchemy ORM model
class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    appointment_time = Column(DateTime(timezone=True), nullable=False)
    vehicle_year = Column(String, nullable=False)
    vehicle_make = Column(String, nullable=False)
    vehicle_model = Column(String, nullable=False)
    problem_description = Column(Text, nullable=False)
    status = Column(String, default="pending")  # pending, confirmed, completed, cancelled
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# Pydantic models for API
class AppointmentBase(BaseModel):
    email: EmailStr
    phone_number: str
    appointment_time: datetime
    vehicle_year: str
    vehicle_make: str
    vehicle_model: str
    problem_description: str

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentUpdate(BaseModel):
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    appointment_time: Optional[datetime] = None
    vehicle_year: Optional[str] = None
    vehicle_make: Optional[str] = None
    vehicle_model: Optional[str] = None
    problem_description: Optional[str] = None
    status: Optional[str] = None

class AppointmentResponse(AppointmentBase):
    id: int
    status: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AppointmentQueueResponse(BaseModel):
    status: str
    message: str
    queue_position: int
    id: int 