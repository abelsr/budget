import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app


@pytest.fixture(name="session")
def session_fixture():
    """SQLite en memoria compartida por conexión (StaticPool)."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with TestingSessionLocal() as session:
        yield session
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    limiter.clear()
    yield
    limiter.clear()


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_db_override():
        yield session

    app.dependency_overrides[get_db] = get_db_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
