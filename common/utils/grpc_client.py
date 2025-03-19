import grpc
import os
from typing import Any, Dict, Optional
from .config import get_settings

# Import generated gRPC code
from ..proto import auth_pb2, auth_pb2_grpc
from ..proto import appointment_pb2, appointment_pb2_grpc
from ..proto import notification_pb2, notification_pb2_grpc

settings = get_settings()

class GrpcClient:
    """Base class for gRPC client communication"""
    
    def __init__(self, channel_address: str):
        self.channel_address = channel_address
        self.channel = grpc.insecure_channel(channel_address)
        
    def close(self):
        """Close the gRPC channel"""
        if self.channel:
            self.channel.close()

class AuthGrpcClient(GrpcClient):
    """gRPC client for Auth Service"""
    
    def __init__(self):
        if not settings.AUTH_SERVICE_GRPC_URL:
            raise ValueError("AUTH_SERVICE_GRPC_URL not configured")
        super().__init__(settings.AUTH_SERVICE_GRPC_URL)
        self.stub = auth_pb2_grpc.AuthServiceStub(self.channel)
        
    def register(self, email: str, password: str, full_name: str):
        """Register a new user"""
        request = auth_pb2.RegisterRequest(
            email=email,
            password=password,
            full_name=full_name
        )
        return self.stub.Register(request)
        
    def login(self, username: str, password: str):
        """Login a user"""
        request = auth_pb2.LoginRequest(
            username=username,
            password=password
        )
        return self.stub.Login(request)
        
    def get_current_user(self, token: str):
        """Get current user from token"""
        request = auth_pb2.TokenRequest(token=token)
        return self.stub.GetCurrentUser(request)
        
    def health_check(self):
        """Check if the auth service is healthy"""
        request = auth_pb2.HealthCheckRequest()
        return self.stub.HealthCheck(request)

class AppointmentGrpcClient(GrpcClient):
    """gRPC client for Appointment Service"""
    
    def __init__(self):
        if not settings.APPOINTMENT_SERVICE_GRPC_URL:
            raise ValueError("APPOINTMENT_SERVICE_GRPC_URL not configured")
        super().__init__(settings.APPOINTMENT_SERVICE_GRPC_URL)
        self.stub = appointment_pb2_grpc.AppointmentServiceStub(self.channel)
        
    def create_appointment(self, token: str, data: Dict[str, Any]):
        """Create a new appointment"""
        request = appointment_pb2.AppointmentRequest(
            token=token,
            email=data.get("email", ""),
            phone_number=data.get("phone_number", ""),
            appointment_time=data.get("appointment_time", ""),
            vehicle_year=data.get("vehicle_year", 0),
            vehicle_make=data.get("vehicle_make", ""),
            vehicle_model=data.get("vehicle_model", ""),
            problem_description=data.get("problem_description", "")
        )
        return self.stub.CreateAppointment(request)
        
    def get_appointments(self, token: str):
        """Get all appointments"""
        request = appointment_pb2.TokenRequest(token=token)
        return self.stub.GetAppointments(request)
        
    def get_appointment(self, token: str, appointment_id: int):
        """Get a specific appointment"""
        request = appointment_pb2.AppointmentIdRequest(
            token=token,
            id=appointment_id
        )
        return self.stub.GetAppointment(request)
        
    def update_appointment(self, token: str, appointment_id: int, data: Dict[str, Any]):
        """Update an appointment"""
        request = appointment_pb2.UpdateAppointmentRequest(
            token=token,
            id=appointment_id,
            email=data.get("email", ""),
            phone_number=data.get("phone_number", ""),
            appointment_time=data.get("appointment_time", ""),
            vehicle_year=data.get("vehicle_year", 0),
            vehicle_make=data.get("vehicle_make", ""),
            vehicle_model=data.get("vehicle_model", ""),
            problem_description=data.get("problem_description", ""),
            status=data.get("status", "")
        )
        return self.stub.UpdateAppointment(request)
        
    def delete_appointment(self, token: str, appointment_id: int):
        """Delete an appointment"""
        request = appointment_pb2.AppointmentIdRequest(
            token=token,
            id=appointment_id
        )
        return self.stub.DeleteAppointment(request)
        
    def health_check(self):
        """Check if the appointment service is healthy"""
        request = appointment_pb2.HealthCheckRequest()
        return self.stub.HealthCheck(request)

class NotificationGrpcClient(GrpcClient):
    """gRPC client for Notification Service"""
    
    def __init__(self):
        if not settings.NOTIFICATION_SERVICE_GRPC_URL:
            raise ValueError("NOTIFICATION_SERVICE_GRPC_URL not configured")
        super().__init__(settings.NOTIFICATION_SERVICE_GRPC_URL)
        self.stub = notification_pb2_grpc.NotificationServiceStub(self.channel)
        
    def send_notification(self, token: str, data: Dict[str, Any]):
        """Send a notification"""
        metadata = {k: str(v) for k, v in data.get("notification_metadata", {}).items()}
        
        request = notification_pb2.NotificationRequest(
            token=token,
            recipient=data.get("recipient", ""),
            notification_type=data.get("notification_type", ""),
            subject=data.get("subject", ""),
            content=data.get("content", ""),
            notification_metadata=metadata
        )
        return self.stub.SendNotification(request)
        
    def get_notifications(self, token: str):
        """Get all notifications"""
        request = notification_pb2.TokenRequest(token=token)
        return self.stub.GetNotifications(request)
        
    def health_check(self):
        """Check if the notification service is healthy"""
        request = notification_pb2.HealthCheckRequest()
        return self.stub.HealthCheck(request) 