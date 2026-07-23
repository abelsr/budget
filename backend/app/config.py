from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración vía variables de entorno (o .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Dev: SQLite. Docker/prod: postgresql+psycopg://budget:budget@db:5432/budget
    database_url: str = "sqlite:///./dev.db"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 días

    # Comprobantes adjuntos: ruta local en dev; en docker ATTACHMENTS_DIR=/data/attachments
    attachments_dir: str = "data/attachments"

    # Escáner de tickets: LLM con visión vía OpenRouter (API compatible
    # con OpenAI). Sin key → endpoint responde 501.
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-3.6-flash"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
