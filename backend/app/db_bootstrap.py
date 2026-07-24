"""Pone la base al día antes de arrancar la API.

Se ejecuta desde el entrypoint del contenedor (`python -m app.db_bootstrap`) y
también sirve en local. Hace dos cosas:

1. **Puente para bases pre-Alembic.** Los despliegues anteriores crearon el
   esquema con `Base.metadata.create_all`, así que tienen las 8 tablas pero no
   `alembic_version`. Un `upgrade head` ahí fallaría con "table households
   already exists". Cuando detecta ese caso, marca la migración inicial como ya
   aplicada (`stamp`) en lugar de re-crear tablas. Es un no-op en bases nuevas
   y en bases ya migradas, así que puede correr en cada arranque.
2. `upgrade head`.

Este puente se puede borrar cuando ya no queden bases creadas antes de Alembic.
"""

import logging
from pathlib import Path

from sqlalchemy import inspect

from alembic import command
from alembic.config import Config
from app.database import engine

logger = logging.getLogger(__name__)

#: Migración que representa el esquema que producía `create_all`.
INITIAL_REVISION = "5d15cfc79c35"

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _is_pre_alembic_database() -> bool:
    """True si el esquema existe pero nadie lo creó con Alembic."""
    with engine.connect() as connection:
        tables = set(inspect(connection).get_table_names())
    return "alembic_version" not in tables and "users" in tables


def main() -> None:
    config = Config(str(ALEMBIC_INI))

    if _is_pre_alembic_database():
        logger.warning(
            "Base creada antes de Alembic: marcándola en %s sin re-crear tablas",
            INITIAL_REVISION,
        )
        command.stamp(config, INITIAL_REVISION)

    command.upgrade(config, "head")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
