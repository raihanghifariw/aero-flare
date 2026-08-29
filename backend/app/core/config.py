"""
Application configuration via pydantic-settings.
All secrets loaded from environment variables — no defaults for secrets.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repo root = three levels up from this file (backend/app/core/config.py).
# Anchoring the .env path here makes config loading independent of CWD
# (works when running uvicorn from backend/, repo root, or Docker).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Fall back to CWD .env if the repo-root file does not exist (Docker images
        # copy only backend/ and provide real env vars instead).
        env_file=str(_ENV_FILE) if _ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Application ---
    ENVIRONMENT: str = "development"
    API_KEY: str = ""
    SECRET_KEY: str = ""

    # --- Database ---
    DATABASE_URL: str = ""
    SQLALCHEMY_POOL_SIZE: int = 5
    SQLALCHEMY_MAX_OVERFLOW: int = 10

    # --- Supabase ---
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_ANON_KEY: str = ""

    # --- Cloudflare R2 ---
    CLOUDFLARE_R2_ACCOUNT_ID: str = ""
    CLOUDFLARE_R2_ACCESS_KEY: str = ""
    CLOUDFLARE_R2_SECRET: str = ""
    CLOUDFLARE_R2_BUCKET_NAME: str = "aero-flare-tiles"

    # --- NASA FIRMS ---
    FIRMS_API_KEY: str = ""

    # --- Ollama ---
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    VLM_MODEL: str = "qwen2-vl:7b"
    VLM_FALLBACK_MODEL: str = "llava:13b"

    # --- XGBoost ---
    XGBOOST_MODEL_PATH: str = "ml/models/xgboost_spread_v1.0.0.ubj"

    # --- Telegram ---
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHANNEL_ID: str = ""

    # --- Grafana / OpenTelemetry ---
    GRAFANA_OTLP_ENDPOINT: str = ""
    GRAFANA_INSTANCE_ID: str = ""
    GRAFANA_API_TOKEN: str = ""

    # --- Open-Meteo ---
    OPEN_METEO_BASE_URL: str = "https://api.open-meteo.com/v1/"

    @field_validator("DATABASE_URL", "FIRMS_API_KEY", "OLLAMA_BASE_URL", "API_KEY", "SECRET_KEY", mode="before")
    @classmethod
    def strip_whitespace(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip().strip("'\"")
        return v

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got: {v!r}")
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings — loaded once at startup."""
    return Settings()  # type: ignore[call-arg]
