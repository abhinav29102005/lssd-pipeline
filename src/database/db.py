"""Database session and initialization utilities."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from src.database.models import Base
from src.utils.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(settings.postgres_dsn, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def init_db() -> None:
    """Create all tables if they do not exist."""
    logger.info("Initializing database schema")
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session() -> Iterator[Session]:
    """Yield a managed SQLAlchemy session."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        logger.exception("Database transaction failed")
        raise
    finally:
        session.close()
