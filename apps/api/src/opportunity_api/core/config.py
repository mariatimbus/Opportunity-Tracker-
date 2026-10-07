"""Application settings via pydantic-settings."""

from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """App settings.

    Env vars use APP_-prefixed aliases (except DATABASE_URL, which follows the
    common convention) so generic variables like DEBUG in the shell cannot
    collide with settings.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="opportunity-api", validation_alias=AliasChoices("APP_NAME"))
    debug: bool = Field(default=False, validation_alias=AliasChoices("APP_DEBUG"))
    # Defaults to a local sqlite file so the app and tests boot without Postgres.
    database_url: str = Field(
        default="sqlite:///./opportunity_tracker.db",
        validation_alias=AliasChoices("DATABASE_URL", "APP_DATABASE_URL"),
    )
    cors_origins: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("CORS_ORIGINS", "APP_CORS_ORIGINS"),
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
