import os

import pytest
from fastapi.testclient import TestClient
from freezegun import freeze_time as _freeze_time
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.core.rate_limit import limiter
from app.main import app
from app.models import Account, Category, Household, User
from tests.helpers import auth_headers, create_user

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


def _session_factory(*, foreign_keys: bool = False):
    """SQLite en memoria compartida por conexión (StaticPool).

    Issue #48: factory con opción ``foreign_keys``. Decisión: FK APAGADAS por
    defecto (comportamiento histórico de la suite) y activas solo donde se
    piden, porque con FK ON la suite NO queda verde sin tocar app:
    - ``import_rows`` tiene FK compuesta hacia
      (transactions.id, transactions.import_batch_id) y algunos tests
      (test_reconciliations) insertan la fila antes de fijar el batch en la
      transacción → IntegrityError real con FK ON.
    - El ciclo deferrable households->users hace fallar ``drop_all`` en el
      teardown si quedan filas.
    ``test_imports`` usa ``session_factory(foreign_keys=True)`` para su
    cobertura del ciclo de vida de imports (antes redefinía el fixture aquí
    shadoweando todo el engine).
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    if foreign_keys:

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with TestingSessionLocal() as session:
        yield session
    # El teardown se hace con FK APAGADAS: con FK ON el ciclo deferrable
    # households->users (fk_households_owner_membership, DEFERRED) hace que
    # DROP TABLE falle si quedan filas (igual que en el fixture antiguo de
    # test_imports). Apagarlas solo para el drop no afecta a la cobertura.
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
    Base.metadata.drop_all(engine)


@pytest.fixture(name="session")
def session_fixture(session_factory):
    yield from session_factory()


@pytest.fixture(name="session_factory")
def session_factory_fixture():
    """Factory de sesiones de test para los tests que necesitan una sesión
    con ``foreign_keys=True`` (test_imports): ``session_factory(
    foreign_keys=True)``."""
    return _session_factory


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


# ---------- Mundo de test consolidado (issue #48) ----------
#
# Sustituye las 8-9 copias locales de ``world_fixture`` (test_core,
# test_recurring, test_forecast, test_alerts, test_budgets, test_goals,
# test_attachments, test_offline_transactions, ...) por una factory
# parametrizable. El fixture ``world`` por defecto es la variante más
# común: dos hogares (h1/h2) con un usuario cada uno y una cuenta "Débito"
# (opening 0) en cada uno; las cuentas y categorías adicionales se crean
# en los tests vía los helpers de tests.helpers (create_account, etc.).
# Las variantes con cuentas/categorías específicas (forecast, alerts,
# goals, attachments) usan ``world_factory`` directamente.


def _world(
    session: Session,
    *,
    users: int = 2,
    emails: tuple[str, ...] = ("uno@example.com", "dos@example.com"),
    names: tuple[str, ...] = ("Uno", "Dos"),
    household_names: tuple[str, ...] = ("Hogar Uno", "Hogar Dos"),
    accounts: tuple[dict, ...] = (),
    categories: tuple[dict, ...] = (),
) -> dict:
    """Crea ``users`` hogares (uno por usuario, el usuario es owner) con
    cuentas/categorías deterministas y regresa un dict con ``h1``/``h2``,
    ``u1``/``u2``, ``headers1``/``headers2``, ``account1``/``account2``
    (primera cuenta de cada hogar, solo si hay cuentas), ``accounts``
    (todas las cuentas en orden de creación) y ``categories`` (todas las
    categorías en orden de creación).

    Cada spec de ``accounts``/``categories`` es un dict de kwargs del
    modelo con la clave ``household`` (índice 1-based del hogar); en
    cuentas, ``owner`` (índice 1-based del usuario) crea una cuenta
    personal de ese miembro."""
    users_: list[User] = [
        create_user(session, email, name) for email, name in zip(emails, names, strict=True)
    ]
    households: list[Household] = []
    for user, name in zip(users_, household_names, strict=True):
        household = Household(name=name, owner_id=user.id)
        session.add(household)
        session.flush()
        user.household_id = household.id
        households.append(household)

    accounts_: list[Account] = []
    for spec in accounts:
        spec = dict(spec)
        household = households[spec.pop("household") - 1]
        owner = spec.pop("owner", None)
        if owner is not None:
            spec["owner_id"] = users_[owner - 1].id
        account = Account(household_id=household.id, **spec)
        session.add(account)
        accounts_.append(account)

    categories_: list[Category] = []
    for spec in categories:
        spec = dict(spec)
        household = households[spec.pop("household") - 1]
        category = Category(household_id=household.id, **spec)
        session.add(category)
        categories_.append(category)

    session.commit()

    world: dict = {}
    for index, (household, user) in enumerate(zip(households, users_, strict=True), start=1):
        world[f"h{index}"] = household
        world[f"u{index}"] = user
        world[f"headers{index}"] = auth_headers(user)
    for index, household in enumerate(households, start=1):
        first = next((a for a in accounts_ if a.household_id == household.id), None)
        if first is not None:
            world[f"account{index}"] = first
    if accounts_:
        world["accounts"] = accounts_
    if categories_:
        world["categories"] = categories_
    return world


@pytest.fixture(name="world_factory")
def world_factory_fixture(session):
    """Factory del fixture ``world`` para variantes con cuentas o
    categorías propias (p. ej. ``world_factory(accounts=(...),
    categories=(...))``); ver ``_world`` para el formato de los specs."""
    return lambda **kwargs: _world(session, **kwargs)


@pytest.fixture(name="world")
def world_fixture(session):
    """Dos hogares aislados, cada uno con su usuario — la variante más
    común (test_core, test_imports, test_transfers, test_merchant_rules,
    test_reconciliations, test_offline_transactions). Las variantes con
    cuentas/categorías propias (test_recurring, test_forecast,
    test_alerts, test_budgets, test_goals, test_attachments) usan
    ``world_factory`` en un fixture fino local."""
    return _world(session)


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
