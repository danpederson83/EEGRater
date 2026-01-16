"""
Database models and connection setup for EEG Rater.
"""
import os
from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Get database URL from environment variable
DATABASE_URL = os.environ.get("DATABASE_URL")

# Handle Render's postgres:// vs postgresql:// URL format
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Create engine - use SQLite fallback for local development
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)
else:
    # Local development fallback
    engine = create_engine("sqlite:///./data/eegrater.db", connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, index=True)
    snippet_id = Column(String, index=True, nullable=False)
    rater = Column(String, index=True, nullable=False)
    rating = Column(Integer, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(Integer, primary_key=True, index=True)
    snippet_a = Column(String, nullable=False)
    snippet_b = Column(String, nullable=False)
    winner = Column(String, nullable=False)
    rater = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Create all tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
