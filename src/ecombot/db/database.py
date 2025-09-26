"""
SQLAlchemy database session and engine management.

This module sets up the asynchronous engine and session factory for the application,
following the standard SQLAlchemy 2.0 async pattern.
"""

from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import declarative_base

from ecombot.config import settings


DATABASE_URL = (
    f"postgresql+asyncpg://{settings.PGUSER}:{settings.PGPASSWORD}@"
    f"{settings.PGHOST}:{settings.PGPORT}/{settings.PGDATABASE}"
)

async_engine = create_async_engine(DATABASE_URL, echo=False)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()
