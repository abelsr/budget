from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


# pool_pre_ping checks the connection is alive before handing it out, so a
# Postgres restart (or a firewall dropping idle connections) no longer surfaces
# as intermittent 500s on the first use of a stale pooled connection (issue #45).
# pool_size / max_overflow make the pool explicit instead of relying on the
# QueuePool defaults (5 / 10).
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Generator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
