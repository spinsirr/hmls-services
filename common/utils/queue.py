import json
from datetime import datetime
import pytz
from typing import Any, Dict, List, Optional
from .cache import redis_client
from .config import get_settings

settings = get_settings()

class MessageQueue:
    """Base class for Redis-based message queues"""
    
    def __init__(self, queue_name: str):
        self.queue_name = queue_name
        self.processing_queue = f"{queue_name}_processing"
        
    async def enqueue(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Add a message to the queue"""
        try:
            # Add timestamp to track when the message was queued
            message["queued_at"] = datetime.now(pytz.UTC).isoformat()
            
            # Serialize the message
            serialized = json.dumps(message)
            
            # Push to the queue
            await redis_client.lpush(self.queue_name, serialized)
            
            # Get queue position
            position = await self.get_queue_length()
            
            return {
                "status": "queued",
                "message": f"Message has been queued for processing",
                "queue_position": position,
                "id": message.get("id")
            }
        except Exception as e:
            print(f"Error in enqueue: {e}")
            raise
            
    async def get_queue_length(self) -> int:
        """Get the current queue length"""
        try:
            return await redis_client.llen(self.queue_name)
        except Exception as e:
            print(f"Error in get_queue_length: {e}")
            return 0
            
    async def dequeue(self) -> Optional[Dict[str, Any]]:
        """Remove and return a message from the queue"""
        try:
            # Atomically move an item from the queue to the processing queue
            message = await redis_client.rpoplpush(self.queue_name, self.processing_queue)
            
            if not message:
                return None
                
            # Parse the message
            return json.loads(message)
        except Exception as e:
            print(f"Error in dequeue: {e}")
            return None
            
    async def complete(self, message: Dict[str, Any]):
        """Mark a message as completed and remove from processing queue"""
        try:
            # Serialize the message to match what's in the processing queue
            message["queued_at"] = message.get("queued_at", datetime.now(pytz.UTC).isoformat())
            serialized = json.dumps(message)
            
            # Remove from processing queue
            await redis_client.lrem(self.processing_queue, 1, serialized)
        except Exception as e:
            print(f"Error in complete: {e}")
            
    async def requeue_failed(self) -> int:
        """Requeue messages that failed processing"""
        try:
            # Get all messages in the processing queue
            processing = await redis_client.lrange(self.processing_queue, 0, -1)
            count = 0
            
            # Move each back to the main queue
            for message in processing:
                await redis_client.lpush(self.queue_name, message)
                await redis_client.lrem(self.processing_queue, 1, message)
                count += 1
                
            return count
        except Exception as e:
            print(f"Error in requeue_failed: {e}")
            return 0
            
    async def add(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for enqueue method to maintain compatibility with existing code"""
        return await self.enqueue(message)

# Predefined queues for different services
class AppointmentQueue(MessageQueue):
    def __init__(self):
        super().__init__("appointment_requests")
        
class NotificationQueue(MessageQueue):
    def __init__(self):
        super().__init__("notification_requests") 