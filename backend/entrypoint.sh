#!/bin/sh
# Migra la base y arranca la API. Compose garantiza que Postgres esté listo
# (`depends_on: db: condition: service_healthy`), así que no hace falta retry.
set -e

/app/.venv/bin/python -m app.db_bootstrap

exec /app/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
