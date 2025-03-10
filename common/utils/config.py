from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional

class BaseServiceSettings(BaseSettings):
    """Base settings class for all services"""
    
    # Service info
    SERVICE_NAME: str
    SERVICE_VERSION: str = "0.1.0"
    
    # Database Settings
    DATABASE_URL: Optional[str] = None
    DB_ECHO: bool = False
    DB_POOL_SIZE: int = 40
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_STATEMENT_TIMEOUT: int = 60000  # 60 seconds
    
    # Redis Settings
    REDIS_URL: str
    REDIS_POOL_SIZE: int = 100
    REDIS_POOL_TIMEOUT: int = 30
    REDIS_MAX_CONNECTIONS: int = 1000
    REDIS_RETRY_ATTEMPTS: int = 3
    REDIS_RETRY_DELAY: float = 0.1  # 100ms
    
    # JWT Settings
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Rate limiting settings
    RATE_LIMIT_TIMES: int = 1000
    RATE_LIMIT_SECONDS: int = 60
    
    # Cache settings
    CACHE_EXPIRE_SECONDS: int = 300
    CACHE_ENABLED: bool = True
    
    # Worker settings
    WORKER_CONCURRENCY: int = 10
    WORKER_PREFETCH_COUNT: int = 50
    WORKER_TASK_TIMEOUT: int = 60  # 60 seconds
    
    # API settings
    API_TIMEOUT: int = 30  # 30 seconds
    API_MAX_CONNECTIONS: int = 100
    
    # Service URLs
    AUTH_SERVICE_URL: Optional[str] = None
    APPOINTMENT_SERVICE_URL: Optional[str] = None
    NOTIFICATION_SERVICE_URL: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings(settings_class=BaseServiceSettings) -> BaseServiceSettings:
    """Get settings instance with caching"""
    return settings_class() 