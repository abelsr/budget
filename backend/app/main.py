import logging
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.routes import (
    accounts,
    alerts,
    attachments,
    auth,
    budgets,
    categories,
    goals,
    households,
    imports,
    merchant_rules,
    reconciliations,
    recurring,
    reports,
    summary,
    tickets,
    transactions,
)
from app.config import settings
from app.database import get_db
from app.logging import configure_logging

# El esquema lo gestiona Alembic: `python -m app.db_bootstrap` (lo corre el
# entrypoint del contenedor) o `uv run alembic upgrade head` en local. Los
# tests siguen usando `create_all` sobre SQLite en memoria (ver conftest).

configure_logging(settings.log_level.upper())
logger = logging.getLogger("app.request")

app = FastAPI(title="Finanzas Familiares API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for module in (
    auth,
    households,
    accounts,
    alerts,
    categories,
    transactions,
    recurring,
    reports,
    attachments,
    summary,
    budgets,
    goals,
    tickets,
    imports,
    merchant_rules,
    reconciliations,
):
    app.include_router(module.router)


@app.middleware("http")
async def log_request(request, call_next):
    request_id = str(uuid4())
    started_at = perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "Request failed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "status": 500,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
            },
        )
        raise

    response.headers["X-Request-ID"] = request_id
    logger.info(
        "Request completed",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return response


@app.get("/health")
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ok"}
