from typing import Literal

from pydantic import Field, HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigurationError(RuntimeError):
    pass


class FindingModelForgeConfig(BaseSettings):
    environment: Literal["development", "testing", "production"] = Field(default="development")

    # Database
    mongo_dsn: SecretStr = Field(default=SecretStr("mongodb://localhost:27017"))
    database_name: str = Field(default="findingmodelforge")

    # OpenAI API
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_default_model: str = Field(default="gpt-4o-mini")

    # Perplexity API
    perplexity_base_url: HttpUrl = Field(default=HttpUrl("https://api.perplexity.ai"))
    perplexity_api_key: SecretStr = Field(default=SecretStr(""))
    perplexity_default_model: str = Field(default="llama-3.1-sonar-large-128k-online")

    model_config = SettingsConfigDict(env_file=".env")

    def check_ready_for_openai(self) -> Literal[True]:
        if not self.openai_api_key.get_secret_value():
            raise ConfigurationError("OpenAI API key is not set")
        return True

    def check_ready_for_perplexity(self) -> Literal[True]:
        if not self.perplexity_api_key.get_secret_value():
            raise ConfigurationError("Perplexity API key is not set")
        return True

    def check_ready_for_database(self) -> Literal[True]:
        if not self.mongo_dsn.get_secret_value():
            raise ConfigurationError("MongoDB DSN is not set")
        return True

    def check_ready_for_mongodb(self) -> Literal[True]:
        self.check_ready_for_database()
        if not self.database_name:
            raise ConfigurationError("Database name is not set")
        return True


settings = FindingModelForgeConfig()
