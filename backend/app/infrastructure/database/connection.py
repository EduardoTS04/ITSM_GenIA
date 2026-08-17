"""Database connection utilities using SQLAlchemy (SQLite)"""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker, declarative_base

from app.core.config import settings


def ensure_sqlite_parent_dir(database_url: str) -> None:
    """Create the parent folder of a SQLite file URL when it is missing.

    The path comes from DATABASE_URL, so local/CI runs never mkdir a hardcoded
    container path such as /app/data. In-memory and non-SQLite URLs are no-ops.
    """
    url = make_url(database_url)
    if not url.drivername.startswith("sqlite"):
        return
    database = url.database
    if not database or database == ":memory:":
        return
    Path(database).expanduser().parent.mkdir(parents=True, exist_ok=True)


# Database URL – see app/core/config.py for the default and env override
DATABASE_URL = settings.DATABASE_URL
ensure_sqlite_parent_dir(DATABASE_URL)

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
