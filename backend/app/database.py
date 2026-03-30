"""
Database Engine & Session Management.

Bachmann: "SQLAlchemy 2.0 style. Type-safe. No lazy loading surprises."
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config import settings


# SQLite needs check_same_thread=False for FastAPI
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    echo=settings.is_development,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


def get_db():
    """
    FastAPI dependency that provides a database session.
    Auto-closes after request completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
