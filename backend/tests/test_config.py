"""Weak secrets must make a production startup fail, not silently run."""

import pytest
from pydantic import ValidationError

from app.config import Settings

STRONG_SECRET = "a" * 64


def test_development_allows_defaults():
    settings = Settings()
    assert settings.app_env == "development"


def test_production_refuses_default_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="dev-secret-change-me")


def test_production_refuses_short_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="production", jwt_secret="too-short")


def test_production_refuses_factory_minio_credentials():
    with pytest.raises(ValidationError, match="MINIO"):
        Settings(app_env="production", jwt_secret=STRONG_SECRET, minio_access_key="minioadmin")
    with pytest.raises(ValidationError, match="MINIO"):
        Settings(app_env="production", jwt_secret=STRONG_SECRET, minio_secret_key="minioadmin123")


def test_production_accepts_strong_configuration():
    settings = Settings(
        app_env="production",
        jwt_secret=STRONG_SECRET,
        minio_access_key="custom-user",
        minio_secret_key="custom-secret-value",
    )
    assert settings.app_env == "production"


def test_app_env_is_case_insensitive():
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(app_env="Production", jwt_secret="dev-secret-change-me")
