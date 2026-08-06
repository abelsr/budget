"""Entorno de Alembic.

La URL de la base **no** se hardcodea en `alembic.ini`: se lee de
`app.config.settings.database_url`, la misma fuente que usa la app (y por
tanto la misma variable `DATABASE_URL` en Docker). Así `alembic upgrade head`
siempre apunta a donde apunta el backend.

Se puede sobreescribir con `sqlalchemy.url` en el objeto Config (vía
`set_main_option`, no en el .ini): lo usan los tests de migraciones, que corren
cada caso contra una base Postgres desechable.
"""

from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.config import settings
from app.database import Base

# Importar los modelos registra las tablas en Base.metadata; sin esto
# --autogenerate no vería nada. (F401: import por efecto secundario.)
from app import models  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """URL del Config si alguien la inyectó; si no, la de la app."""
    return config.get_main_option("sqlalchemy.url") or settings.database_url


def run_migrations_offline() -> None:
    """Genera el SQL sin conectarse (`alembic upgrade head --sql`)."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_database_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
