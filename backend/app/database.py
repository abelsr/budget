from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


# pool_pre_ping checks the connection is alive before handing it out, so a
# Postgres restart (or a firewall dropping idle connections) no longer surfaces
# as intermittent 500s on the first use of a stale pooled connection (issue #45).
# The pool is per-process: with N Uvicorn workers the total is
# N * (db_pool_size + db_max_overflow), so both are configurable via Settings
# (env vars DB_POOL_SIZE / DB_MAX_OVERFLOW) instead of hard-coded.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
