import secrets

from findingmodelforge.config import FindingModelForgeConfig, QuoteStrippedSecretStr, QuoteStrippedStr
from pydantic import Field
from typing_extensions import Final

GITHUB_AUTHORIZE_URL: Final[str] = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL: Final[str] = "https://github.com/login/oauth/access_token"
GITHUB_USER_INFO_URL: Final[str] = "https://api.github.com/user"
LOGIN_PATH: Final[str] = "/login"
AUTH_REDIRECT_URI: Final[str] = "http://localhost:8000/callback"
DEFAULT_PORT: Final[int] = 8000


class FindingModelForgeAPIConfig(FindingModelForgeConfig):
    port: int = Field(default=DEFAULT_PORT)

    github_authorize_url: str = Field(default=GITHUB_AUTHORIZE_URL)
    github_access_token_url: str = Field(default=GITHUB_ACCESS_TOKEN_URL)
    github_user_info_url: str = Field(default=GITHUB_USER_INFO_URL)

    github_client_id: QuoteStrippedStr
    github_client_secret: QuoteStrippedSecretStr

    login_path: str = Field(default=LOGIN_PATH)
    auth_redirect_uri: str = Field(default=AUTH_REDIRECT_URI)

    storage_secret: QuoteStrippedSecretStr = Field(
        default_factory=lambda: QuoteStrippedSecretStr(secrets.token_hex(16))
    )

    enable_ssl: bool = Field(default=False)
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None


settings = FindingModelForgeAPIConfig()  # type: ignore
