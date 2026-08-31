FROM python:3.14-slim

# Pinned to an exact release (not a floating tag) so builds are reproducible.
COPY --from=ghcr.io/astral-sh/uv:0.12.7 /uv /usr/local/bin/uv

# The app runs as an unprivileged user. /app is the only place it reads from;
# it writes nothing to disk at runtime (logs go to stdout, Alembic only reads
# alembic.ini and talks to the database), so it never needs root.
RUN useradd --create-home app

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic
COPY entrypoint.sh ./
# Hand the whole tree (including the venv uv just created) to the app user.
RUN chmod +x entrypoint.sh && chown -R app:app /app

USER app

EXPOSE 8000
# El entrypoint corre las migraciones antes de uvicorn.
CMD ["/app/entrypoint.sh"]
