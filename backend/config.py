"""Centralized application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
FRONTEND_DIR = ROOT_DIR / "frontend"
MODELS_DIR = ROOT_DIR / "models"
DB_PATH = DATA_DIR / "app.db"


@dataclass
class AppConfig:
    """Application settings loaded from environment variables."""

    # App
    debug: bool = False
    secret_key: str = "micro-expression-demo-secret-key-2024"
    app_title: str = "微表情识别商业化原型"
    app_version: str = "5.0.0"

    # Database
    db_type: str = "sqlite"
    mysql_host: str = "localhost"
    mysql_user: str = "root"
    mysql_password: str = "rootpassword"
    mysql_db: str = "micro_expression"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    # CORS
    cors_origins: list[str] = field(default_factory=lambda: ["http://localhost:3000", "http://localhost:8000", "http://localhost:8080"])

    # AI Inference
    inference_mode: str = "demo"  # demo / pytorch / onnx
    inference_confidence_threshold: float = 0.3

    # Auth
    access_token_ttl: int = 7200  # 2 hours
    refresh_token_ttl: int = 604800  # 7 days

    # Stripe
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_public_key: str = ""

    # SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""

    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_auth_per_minute: int = 10
    rate_limit_api_per_minute: int = 60
    rate_limit_enterprise_per_minute: int = 300

    # Activation codes (comma-separated: "CODE:tier:days:credits,CODE:tier:days:credits")
    activation_codes: str = "BASIC_30D_10R:普通会员:30:10,PRO_30D_99R:高级会员:30:99,ENTERPRISE_365D_999R:企业会员:365:999"

    # Request limits
    max_body_size_mb: int = 10


def load_config() -> AppConfig:
    """Load configuration from environment variables."""
    return AppConfig(
        debug=os.getenv("APP_DEBUG", "false").lower() == "true",
        secret_key=os.getenv("APP_SECRET_KEY", AppConfig.secret_key),
        app_title=os.getenv("APP_TITLE", AppConfig.app_title),
        app_version=os.getenv("APP_VERSION", AppConfig.app_version),
        db_type=os.getenv("DB_TYPE", "sqlite"),
        mysql_host=os.getenv("MYSQL_HOST", "localhost"),
        mysql_user=os.getenv("MYSQL_USER", "root"),
        mysql_password=os.getenv("MYSQL_PASSWORD", "rootpassword"),
        mysql_db=os.getenv("MYSQL_DB", "micro_expression"),
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        cors_origins=_parse_cors_origins(os.getenv("CORS_ORIGINS", "")),
        inference_mode=os.getenv("APP_INFERENCE_MODE", "demo"),
        inference_confidence_threshold=float(os.getenv("INFERENCE_CONFIDENCE_THRESHOLD", "0.3")),
        access_token_ttl=int(os.getenv("ACCESS_TOKEN_TTL", "7200")),
        refresh_token_ttl=int(os.getenv("REFRESH_TOKEN_TTL", "604800")),
        stripe_api_key=os.getenv("STRIPE_API_KEY", ""),
        stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
        stripe_public_key=os.getenv("STRIPE_PUBLIC_KEY", ""),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=os.getenv("SMTP_USERNAME", ""),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        activation_codes=os.getenv("ACTIVATION_CODES", AppConfig.activation_codes),
        rate_limit_enabled=os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true",
        rate_limit_auth_per_minute=int(os.getenv("RATE_LIMIT_AUTH_PER_MINUTE", "10")),
        rate_limit_api_per_minute=int(os.getenv("RATE_LIMIT_API_PER_MINUTE", "60")),
        rate_limit_enterprise_per_minute=int(os.getenv("RATE_LIMIT_ENTERPRISE_PER_MINUTE", "300")),
        max_body_size_mb=int(os.getenv("MAX_BODY_SIZE_MB", "10")),
    )


def _parse_cors_origins(raw: str) -> list[str]:
    if not raw.strip():
        return AppConfig().cors_origins
    return [o.strip() for o in raw.split(",") if o.strip()]


# Load .env file before reading config
from dotenv import load_dotenv
load_dotenv(ROOT_DIR / ".env")

# Load config once at module import
config: AppConfig = load_config()


def reload_config() -> AppConfig:
    """Reload configuration (useful for testing)."""
    global config
    config = load_config()
    return config
