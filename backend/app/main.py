from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import (
    accounts,
    attachments,
    auth,
    categories,
    households,
    summary,
    tickets,
    transactions,
)
from app.config import settings
from app.database import Base, engine

# Dev: crea tablas al arrancar. Alembic llegará en la siguiente iteración.
Base.metadata.create_all(bind=engine)

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
    attachments,
    summary,
    tickets,
):
    app.include_router(module.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
