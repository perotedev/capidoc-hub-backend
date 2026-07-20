from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, populated from environment variables / .env file."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    app_name: str = "CapiDoc API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    # PostgreSQL
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "capidoc"
    postgres_user: str = "capidoc"
    postgres_password: str = "capidoc"

    # MongoDB
    mongo_host: str = "mongodb"
    mongo_port: int = 27017
    mongo_db: str = "capidoc"
    mongo_user: str = "capidoc"
    mongo_password: str = "capidoc"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Auth / JWT
    jwt_secret_key: str = "change-this-secret-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Object storage (S3 / MinIO)
    s3_endpoint_url: str = "http://minio:9000"
    s3_region: str = "us-east-1"
    s3_access_key_id: str = "capidoc"
    s3_secret_access_key: str = "capidoc12345"
    s3_bucket_name: str = "capidoc-files"
    s3_use_path_style: bool = True
    file_url_expire_seconds: int = 86400

    # CORS
    cors_origins: str = "http://localhost:4200"

    # Email (Resend) — when disabled (dev default), emails are logged instead of sent
    email_enabled: bool = False
    resend_api_key: str = ""
    email_from_address: str = "CapiDoc <no-reply@capidoc.com>"

    # Frontend (used to build links embedded in emails)
    frontend_url: str = "http://localhost:4200"

    # Password reset (OTP code, delivered by email)
    password_reset_code_expire_minutes: int = 15
    password_reset_cooldown_seconds: int = 60
    password_reset_max_attempts: int = 5

    # Dev seed — auto-creates this super admin on startup if no user with this
    # email exists yet. Leave `default_admin_email` blank to disable.
    default_admin_email: str = ""
    default_admin_password: str = ""
    default_admin_name: str = "Admin"

    # n8n document-extraction integration — leave `n8n_extraction_webhook_url`
    # blank to disable (imports fail immediately with a clear message instead
    # of hanging forever). `api_public_base_url` must be an address n8n can
    # reach to call `callback_url` back, which usually isn't `localhost`.
    n8n_extraction_webhook_url: str = ""
    n8n_callback_secret: str = "change-this-secret-in-production"
    api_public_base_url: str = "http://localhost:8000"

    # WhatsApp bot conversation — n8n relays WAHA messages to this backend
    # (n8n owns the WAHA connection/credentials, not this backend).
    whatsapp_webhook_secret: str = "change-this-secret-in-production"

    @property
    def postgres_dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def mongo_dsn(self) -> str:
        return (
            f"mongodb://{self.mongo_user}:{self.mongo_password}"
            f"@{self.mongo_host}:{self.mongo_port}/{self.mongo_db}?authSource=admin"
        )

    @property
    def redis_dsn(self) -> str:
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor — reads the environment only once per process."""
    return Settings()
