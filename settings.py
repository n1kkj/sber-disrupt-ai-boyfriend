from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseSettings):
    host: str = 'db'
    port: int = 5432
    name: str = 'postgres'
    user: str = 'postgres'
    password: str = 'postgres'
    model_config = SettingsConfigDict(env_prefix='DB_', env_file='.env', extra='ignore')


class AuthConfig(BaseSettings):
    secret: str = 'change-me-in-production'
    expire_minutes: int = 10080
    model_config = SettingsConfigDict(env_prefix='JWT_', env_file='.env', extra='ignore')


class GeminiConfig(BaseSettings):
    api_key: str = ''
    model: str = 'gemini-2.5-flash'
    embedding_model: str = 'gemini-embedding-001'
    base_url: str = 'https://generativelanguage.googleapis.com/v1beta/openai/'
    proxy_url: Optional[str] = None
    model_config = SettingsConfigDict(env_prefix='GEMINI_', env_file='.env', extra='ignore')


class TelegramConfig(BaseSettings):
    bot_token: str = ''
    bot_username: str = ''
    webhook_secret: str = ''
    mode: str = 'webhook'
    polling_timeout: int = 25
    link_token_ttl_minutes: int = 10
    proxy_url: Optional[str] = None
    model_config = SettingsConfigDict(env_prefix='TELEGRAM_', env_file='.env', extra='ignore')


class RedisConfig(BaseSettings):
    url: str = 'redis://redis:6379/0'
    task_state_ttl_seconds: int = 86400
    model_config = SettingsConfigDict(env_prefix='REDIS_', env_file='.env', extra='ignore')


class CeleryConfig(BaseSettings):
    default_queue: str = 'messages'
    max_retries: int = 3
    retry_backoff_seconds: int = 5
    retry_backoff_max_seconds: int = 300
    task_time_limit_seconds: int = 180
    model_config = SettingsConfigDict(env_prefix='CELERY_', env_file='.env', extra='ignore')


class Settings(BaseSettings):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    celery: CeleryConfig = Field(default_factory=CeleryConfig)
    debug: bool = True
    app_title: str = 'AI boyfriend MVP'
    platform_url: str = 'http://localhost:3000'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def sqlalchemy_database_url(self) -> str:
        return f'postgresql+asyncpg://{self.db.user}:{self.db.password}@{self.db.host}:{self.db.port}/{self.db.name}'


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


config = get_settings()
