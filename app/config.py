from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Content & Subscription Management API"
    API_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql+psycopg://postgres:postgres@localhost:5432/content_db"
    REDIS_URL: str = "redis://localhost:6379/0"

    JWT_SECRET_KEY: str = "change-this-secret-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    CACHE_TTL_SECONDS: int = 60
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    FIRST_ADMIN_EMAIL: str | None = None
    FIRST_ADMIN_PASSWORD: str | None = None


settings = Settings()
