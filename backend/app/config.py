from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración vía variables de entorno (o .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://budget:budget@localhost:5432/budget"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 días

    # Process-local limits. Appropriate for the single-process self-host setup;
    # use a shared limiter before running multiple backend replicas.
    auth_register_limit: int = Field(default=5, gt=0)
    auth_register_window_seconds: int = Field(default=3600, gt=0)
    auth_login_limit: int = Field(default=10, gt=0)
    auth_login_window_seconds: int = Field(default=60, gt=0)
    auth_join_limit: int = Field(default=10, gt=0)
    auth_join_window_seconds: int = Field(default=60, gt=0)
    ticket_scan_limit: int = Field(default=10, gt=0)
    ticket_scan_window_seconds: int = Field(default=3600, gt=0)

    max_members_per_household: int = Field(default=10, gt=0)
    max_active_invitations_per_household: int = Field(default=5, gt=0)

    # Comprobantes adjuntos: almacenamiento S3 (MinIO). Endpoint sin scheme.
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "attachments"
    minio_secure: bool = False

    # Escáner de tickets: LLM con visión vía OpenRouter (API compatible
    # con OpenAI). Sin key → endpoint responde 501.
    openrouter_api_key: str | None = None
    openrouter_model: str = "google/gemini-3.6-flash"

    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


settings = Settings()
