from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    accounts,
    attachments,
    auth,
    budgets,
    categories,
    goals,
    households,
    imports,
    reconciliations,
    recurring,
    reports,
    summary,
    tickets,
    transactions,
)
from app.config import settings

# El esquema lo gestiona Alembic: `python -m app.db_bootstrap` (lo corre el
# entrypoint del contenedor) o `uv run alembic upgrade head` en local. Los
# tests siguen usando `create_all` sobre SQLite en memoria (ver conftest).

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
    reconciliations,
):
    app.include_router(module.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
