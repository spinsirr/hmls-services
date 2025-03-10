import httpx
from typing import Any, Dict, Optional
from .config import get_settings
import json
import asyncio
from fastapi import HTTPException, status

settings = get_settings()

class ServiceClient:
    """Base class for service-to-service communication"""
    
    def __init__(self, base_url: str, timeout: int = None):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout or settings.API_TIMEOUT
        
    async def _request(
        self, 
        method: str, 
        endpoint: str, 
        data: Any = None, 
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """Make an HTTP request to another service"""
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        timeout = timeout or self.timeout
        
        default_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        if headers:
            default_headers.update(headers)
            
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=default_headers
                )
                
                # Raise for HTTP errors
                response.raise_for_status()
                
                # Return JSON response
                return response.json()
        except httpx.HTTPStatusError as e:
            # Handle HTTP errors (4xx, 5xx)
            error_detail = f"Service request failed: {str(e)}"
            try:
                error_json = e.response.json()
                if "detail" in error_json:
                    error_detail = error_json["detail"]
            except:
                pass
                
            raise HTTPException(
                status_code=e.response.status_code,
                detail=error_detail
            )
        except httpx.RequestError as e:
            # Handle request errors (connection, timeout)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Service unavailable: {str(e)}"
            )
        except Exception as e:
            # Handle unexpected errors
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal error: {str(e)}"
            )
            
    async def get(self, endpoint: str, params: Dict[str, Any] = None, **kwargs) -> Dict[str, Any]:
        """Make a GET request"""
        return await self._request("GET", endpoint, params=params, **kwargs)
        
    async def post(self, endpoint: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Make a POST request"""
        return await self._request("POST", endpoint, data=data, **kwargs)
        
    async def put(self, endpoint: str, data: Any = None, **kwargs) -> Dict[str, Any]:
        """Make a PUT request"""
        return await self._request("PUT", endpoint, data=data, **kwargs)
        
    async def delete(self, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make a DELETE request"""
        return await self._request("DELETE", endpoint, **kwargs)

# Predefined clients for different services
class AuthServiceClient(ServiceClient):
    def __init__(self):
        if not settings.AUTH_SERVICE_URL:
            raise ValueError("AUTH_SERVICE_URL not configured")
        super().__init__(settings.AUTH_SERVICE_URL)
        
class AppointmentServiceClient(ServiceClient):
    def __init__(self):
        if not settings.APPOINTMENT_SERVICE_URL:
            raise ValueError("APPOINTMENT_SERVICE_URL not configured")
        super().__init__(settings.APPOINTMENT_SERVICE_URL)
        
class NotificationServiceClient(ServiceClient):
    def __init__(self):
        if not settings.NOTIFICATION_SERVICE_URL:
            raise ValueError("NOTIFICATION_SERVICE_URL not configured")
        super().__init__(settings.NOTIFICATION_SERVICE_URL) 