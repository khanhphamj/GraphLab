"""Database session management"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/graphlab")

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,    # Recycle connections every 5 minutes
    echo=os.getenv("SQL_DEBUG", "false").lower() == "true"  # Enable SQL logging if needed
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()