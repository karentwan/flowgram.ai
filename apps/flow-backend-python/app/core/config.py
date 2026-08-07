"""Flowgram Studio Python backend configuration.

All values come from environment variables, mirroring the Node backend's
``apps/flow-backend/src/config.ts`` one-for-one so both backends can run against
the same ``.env`` and the same database.

Generate a 32-byte base64 master key with:
    python -c "import secrets, base64; print(base64.b64encode(secrets.token_bytes(32)).decode())"
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # HTTP server
    port: int = Field(default=4001, validation_alias="PORT")
    """Server port. Defaults to 4001 (Node backend occupies 4000) so both can run side by side."""

    host: str = Field(default="0.0.0.0", validation_alias="HOST")

    node_env: str = Field(default="development", validation_alias="NODE_ENV")

    # Database (same connection string the Node/Prisma backend uses)
    database_url: str = Field(default="", validation_alias="DATABASE_URL")

    # 32-byte base64 master key for encrypting secrets at rest. Must match the
    # Node backend's FLOWGRAM_ENCRYPTION_KEY for cross-compat of enc:: payloads.
    flowgram_encryption_key: str = Field(default="", validation_alias="FLOWGRAM_ENCRYPTION_KEY")

    # Comma-separated allowed editor origins (CORS).
    cors_origin: str = Field(default="http://localhost:3000", validation_alias="CORS_ORIGIN")

    @field_validator("flowgram_encryption_key")
    @classmethod
    def _validate_encryption_key(cls, v: str) -> str:
        # Empty key is allowed at import time (e.g. for `--help`); the crypto
        # module enforces the 32-byte length lazily when actually used.
        return v

    @property
    def cors_origins(self) -> list[str]:
        """CORS origins parsed from the comma-separated env var."""
        return [o.strip() for o in self.cors_origin.split(",") if o.strip()]

    @property
    def is_dev(self) -> bool:
        return self.node_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
