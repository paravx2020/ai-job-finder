"""SQLite database setup and models using SQLAlchemy."""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, create_engine
)
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker

from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

__all__ = [
    "Base",
    "UserProfile",
    "User",
    "JobPosting",
    "Application",
    "CVImprovementLog",
    "init_db",
    "get_engine",
    "get_session",
    "session_scope",
    "find_job_by_url",
]


# ── Models ──────────────────────────────────────────────────────────────────

class UserProfile(Base):
    """User profile with preferences and contact info."""
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    phone = Column(String(50), nullable=True)
    default_domain = Column(String(100), default="software engineering")
    default_location = Column(String(255), nullable=True)
    preferences = Column(JSON, nullable=True)  # custom preferences
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    email = Column(String(255), unique=True)
    raw_cv_path = Column(String(500))
    parsed_cv = Column(JSON)          # structured CV data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class JobPosting(Base):
    __tablename__ = "job_postings"
    id = Column(Integer, primary_key=True)
    source = Column(String(50))        # linkedin, indeed, glassdoor
    title = Column(String(255))
    company = Column(String(255))
    description = Column(Text)
    url = Column(String(1000), unique=True)
    salary = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    posted_date = Column(DateTime, nullable=True)
    last_scraped = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    status = Column(String(50), default="pending")  # pending, submitted, rejected, interview
    match_score = Column(Float)
    match_reason = Column(Text)
    applied_at = Column(DateTime, nullable=True)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    job = relationship("JobPosting", backref="applications")


class CVImprovementLog(Base):
    __tablename__ = "cv_improvement_logs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    section = Column(String(100))
    original_text = Column(Text)
    improved_text = Column(Text)
    model_used = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)


# ── Database Functions ──────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't exist.

    For production use, prefer `run_migrations()` instead.
    """
    Base.metadata.create_all(engine)


def get_engine():
    """Return the SQLAlchemy engine.

    Useful for test isolation — pass a test engine to override the default.
    """
    return engine


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations.

    Usage:
        with session_scope() as session:
            user = User(name="Alice", email="alice@example.com")
            session.add(user)
            # Commits automatically on success
            # Rolls back on exception
            # Always closes the session

    This is the preferred way to interact with the database.
    """
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_session() -> Session:
    """Return a new database session.

    .. deprecated::
        Use :func:`session_scope` instead for automatic commit/rollback/close.
        This function is kept for backward compatibility.

    Returns:
        A new SQLAlchemy Session instance.
    """
    return SessionLocal()



def find_job_by_url(session, url: str):
    """Find an existing job posting by URL.

    Args:
        session: SQLAlchemy session.
        url: The job posting URL to search for.

    Returns:
        JobPosting if found, None otherwise.
    """
    return session.query(JobPosting).filter(JobPosting.url == url).first()

def run_migrations() -> None:
    """Run Alembic migrations to bring the database to the latest schema.

    Falls back to init_db() if Alembic is not configured.
    """
    try:
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config('alembic.ini')
        command.upgrade(alembic_cfg, 'head')
    except Exception:
        # Fallback: create tables directly if Alembic fails
        init_db()
