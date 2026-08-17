"""Database connection utilities using SQLAlchemy (SQLite)"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings

# Database URL – see app/core/config.py for the default and env override
DATABASE_URL = settings.DATABASE_URL

# echo=False for production; set to True for debugging
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, echo=False)

# SessionLocal class – each request gets a new session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_db():
    """FastAPI dependency that yields a DB session and closes it afterwards."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
