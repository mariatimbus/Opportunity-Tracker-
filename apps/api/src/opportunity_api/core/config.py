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
    # Supabase Auth — tokens are issued by Supabase (GoTrue), the backend only
    # validates them. Set in every environment (Supabase Project Settings → API).
    supabase_url: str = Field(default="", validation_alias=AliasChoices("APP_SUPABASE_URL"))
    supabase_jwt_secret: str = Field(
        default="", validation_alias=AliasChoices("APP_SUPABASE_JWT_SECRET")
    )
    supabase_jwt_audience: str = Field(
        default="authenticated", validation_alias=AliasChoices("APP_SUPABASE_JWT_AUDIENCE")
    )
    # Fixed-window per-client-IP limit (requests/minute); 0 or negative disables.
    rate_limit_per_minute: int = Field(
        default=240, validation_alias=AliasChoices("APP_RATE_LIMIT_PER_MINUTE")
    )
    # Optional AI matching (A11/A12). Empty ollama_url disables the AI
    # component entirely; the deterministic matching core keeps working.
    ollama_url: str = Field(default="", validation_alias=AliasChoices("APP_OLLAMA_URL"))
    ollama_embed_model: str = Field(
        default="nomic-embed-text", validation_alias=AliasChoices("APP_OLLAMA_EMBED_MODEL")
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    # Cached so repeated calls (e.g. per-request in RateLimitMiddleware) don't re-parse env.
    return Settings()
