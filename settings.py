from functools import lru_cache

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
    model_config = SettingsConfigDict(env_prefix='GEMINI_', env_file='.env', extra='ignore')


class TelegramConfig(BaseSettings):
    bot_token: str = ''
    webhook_secret: str = ''
    model_config = SettingsConfigDict(env_prefix='TELEGRAM_', env_file='.env', extra='ignore')


class Settings(BaseSettings):
    db: DatabaseConfig = Field(default_factory=DatabaseConfig)
    auth: AuthConfig = Field(default_factory=AuthConfig)
    gemini: GeminiConfig = Field(default_factory=GeminiConfig)
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    debug: bool = True
    app_title: str = 'AI boyfriend MVP'
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def sqlalchemy_database_url(self) -> str:
        return f'postgresql+asyncpg://{self.db.user}:{self.db.password}@{self.db.host}:{self.db.port}/{self.db.name}'


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


config = get_settings()
