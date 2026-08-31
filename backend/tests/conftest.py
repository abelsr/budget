import os

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time as _freeze_time
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app

#: Fecha fija (mediado de mes y de año, sin bordes) para los tests que
#: dependen de date.today()/datetime.now() (issue #49).
FROZEN_NOW = "2026-08-15 12:00:00"


@pytest.fixture(name="freeze_time")
def freeze_time_fixture():
    """Congela el reloj en FROZEN_NOW para que los tests de fechas sean
    deterministas cualquier día del año.

    Scope por función (no autouse): solo lo piden los tests que usan fechas
    reales; el resto no debe acoplarse al reloj congelado. Los tests que lo
    usan declaran `freeze_time` ANTES de `world`/`client`/`card_world` en sus
    parámetros: pytest resuelve los fixtures en el orden de la firma, así que
    el reloj queda congelado antes de que esos fixtures construyan JWTs
    (exp = now + 1h) y datos relativos a "hoy".
    """
    with _freeze_time(FROZEN_NOW, tz_offset=0):
        yield


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


def pytest_addoption(parser):
    parser.addoption("--skip-db", action="store_true", default=False, help="Deselecciona los tests marcados @pytest.mark.db")


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items):
    skip_db = config.getoption("--skip-db")
    if skip_db:
        skip = pytest.mark.skip(reason="--skip-db")
        for item in items:
            if "db" in item.keywords:
                item.add_marker(skip)
        return

    # CI backstop: con MIGRATIONS_TEST_REQUIRED=1 y sin base, los tests de
    # migraciones deben reventar en vez de saltarse (falso verde). Vive aquí y
    # no al importar test_migrations.py para que `-m "not db"` / `--skip-db`
    # puedan excluirlos sin que el import falle. Un fixture de module scope no
    # sirve para esto: no se ejecuta cuando todos los tests quedan
    # skipif-skipped, que es justo el caso de falso verde.
    if (
        os.environ.get("MIGRATIONS_TEST_REQUIRED") == "1"
        and not os.environ.get("MIGRATIONS_TEST_DATABASE_URL")
        and any("db" in item.keywords for item in items)
    ):
        raise RuntimeError(
            "MIGRATIONS_TEST_REQUIRED=1 pero falta MIGRATIONS_TEST_DATABASE_URL: "
            "el servicio de Postgres no llegó."
        )
