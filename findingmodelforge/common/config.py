import secrets
import sys

from loguru import logger
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Final

GITHUB_AUTHORIZE_URL: Final[str] = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL: Final[str] = "https://github.com/login/oauth/access_token"
GITHUB_USER_INFO_URL: Final[str] = "https://api.github.com/user"
LOGIN_PATH: Final[str] = "/login"
AUTH_REDIRECT_URI: Final[str] = "http://localhost:8000/callback"


def generate_storage_secret() -> SecretStr:
    return SecretStr(secrets.token_hex(16))


class FindingModelForgeAPIConfig(BaseSettings):
    github_authorize_url: str = Field(default=GITHUB_AUTHORIZE_URL)
    github_access_token_url: str = Field(default=GITHUB_ACCESS_TOKEN_URL)
    github_user_info_url: str = Field(default=GITHUB_USER_INFO_URL)

    github_client_id: str | None = None
    github_client_secret: SecretStr | None = None

    login_path: str = Field(default=LOGIN_PATH)
    # TODO: This shouldn't be being passed around like this; should figure out how to fix it sometime
    auth_redirect_uri: str = Field(default=AUTH_REDIRECT_URI)

    storage_secret: SecretStr = Field(default_factory=generate_storage_secret)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Loguru setup
logger.remove()
logger.add("fmf-web.log", rotation="1 week", retention="1 month", level="WARNING")
logger.add(
    sys.stderr,
    format="<green>FMF {level}</green>: <level>{message}</level> [{time:YY-MM-DD HH:mm:ss}]",
    colorize=True,
    level="INFO",
)

settings = FindingModelForgeAPIConfig()
if settings.github_client_id is None or settings.github_client_secret is None:
    raise ValueError(
        "GitHub client ID and secret must be set in the environment or .env file. "
        "Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET."
    )
