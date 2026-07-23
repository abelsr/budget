from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración vía variables de entorno (o .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Dev: SQLite. Docker/prod: postgresql+psycopg://budget:budget@db:5432/budget
    database_url: str = "sqlite:///./dev.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7  # 7 días

    # Escáner de tickets: proveedor de visión (opcional; sin key → 501)
    gemini_api_key: str | None = None

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
