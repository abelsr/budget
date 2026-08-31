from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración vía variables de entorno (o .env)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    #: development (default) | production. En production los secretos débiles
    #: hacen fallar el arranque en vez de arrancar con JWTs falsables.
    app_env: str = "development"

    database_url: str = "postgresql+psycopg://budget:budget@localhost:5432/budget"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    #: Access tokens are short-lived; a 30-day token (the old default) lived a
    #: month after a password change / member removal / device theft.
    jwt_expire_minutes: int = 15
    #: Window during which an expired access token can be renewed via
    #: POST /auth/refresh (backed by the refresh_tokens table, one row per
    #: issued token keyed by its jti).
    refresh_token_expiry_days: int = 30

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

    log_level: str = "INFO"

    @model_validator(mode="after")
    def _refuse_weak_secrets_in_production(self) -> "Settings":
        """Fail fast: a known/default secret must never guard real sessions.

        In development the defaults are fine; in production the app refuses
        to start instead of issuing forgeable JWTs or trusting MinIO with
        factory credentials.
        """
        if self.app_env.lower() != "production":
            return self
        if len(self.jwt_secret) < 32 or self.jwt_secret == "dev-secret-change-me":
            raise ValueError(
                "JWT_SECRET must be a unique value of at least 32 bytes in "
                "production (e.g. `openssl rand -hex 32`). Refusing to start "
                "with the development default."
            )
        if self.minio_access_key == "minioadmin" or self.minio_secret_key in {"minioadmin", "minioadmin123"}:
            raise ValueError(
                "MINIO_ACCESS_KEY / MINIO_SECRET_KEY must not be the factory "
                "credentials (minioadmin) in production. Set unique values."
            )
        return self


settings = Settings()
