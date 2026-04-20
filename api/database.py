"""
Database setup — SQLAlchemy async engine.

Uses SQLite by default (zero-config for development).
Switch to PostgreSQL by changing DATABASE_URL in .env:
  DATABASE_URL=postgresql+asyncpg://user:pass@host/dbname
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./sentinel.db")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    # SQLite-specific: allow the same connection to be used across threads
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Create all tables on first startup."""
    async with engine.begin() as conn:
        from api import models  # noqa: F401 — ensures models are registered
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency that yields a DB session."""
    async with AsyncSessionLocal() as session:
        yield session
