from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from .config import get_settings

settings = get_settings()

# Convert PostgreSQL URL to async
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace(
    'postgresql://', 'postgresql+asyncpg://'
) if settings.DATABASE_URL else None

# Create async engine with optimized settings
engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=settings.DB_ECHO,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    connect_args={
        "server_settings": {
            "jit": "off",
            "statement_timeout": str(settings.DB_STATEMENT_TIMEOUT),
            "idle_in_transaction_session_timeout": str(settings.DB_STATEMENT_TIMEOUT),
        },
        "command_timeout": 60
    }
) if ASYNC_DATABASE_URL else None

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
) if engine else None

Base = declarative_base()

@asynccontextmanager
async def get_db_session():
    """Async context manager for database sessions"""
    if not AsyncSessionLocal:
        raise ValueError("Database connection not configured")
        
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        raise
    finally:
        await session.close()

async def init_db():
    """Initialize database tables"""
    if not engine:
        return
        
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all) 