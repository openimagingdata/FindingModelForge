import secrets

from loguru import logger as logger
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore")

    # App Configuration
    app_name: str = "Finding Model Forge"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Security
    secret_key: SecretStr = Field(default_factory=lambda: SecretStr(secrets.token_hex(32)))
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # GitHub OAuth Configuration
    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None
    github_authorize_url: str = "https://github.com/login/oauth/authorize"
    github_token_url: str = "https://github.com/login/oauth/access_token"
    github_user_url: str = "https://api.github.com/user"

    # Application URLs
    base_url: str = "http://localhost:8000"

    # Proxy Configuration
    # Set to specific IPs for security (e.g., "172.18.0.1,10.0.0.1") or "*" to trust all
    forwarded_allow_ips: str = "*"

    # MongoDB Configuration
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "findingmodels"

    @property
    def github_redirect_uri(self) -> str:
        """GitHub OAuth redirect URI."""
        return f"{self.base_url}/auth/callback"

    def get_secret_key(self) -> str:
        """Get the secret key as a string."""
        return self.secret_key.get_secret_value()


# Global settings instance
settings = Settings()
