import os
import secrets
from typing_extensions import Final
from dotenv import load_dotenv

GITHUB_AUTHORIZE_URL: Final[str] = "https://github.com/login/oauth/authorize"
GITHUB_ACCESS_TOKEN_URL: Final[str] = "https://github.com/login/oauth/access_token"
GITHUB_USER_INFO_URL: Final[str] = "https://api.github.com/user"
LOGIN_PATH: Final[str] = "/login"
DEFAULT_PORT = 8000


class Config:
    client_id: str | None
    client_secret: str | None
    redirect_uri: str | None
    state: str | None
    storage_secret: str | None
    enable_ssl: bool = False
    ssl_certfile: str | None = None
    ssl_keyfile: str | None = None
    github_authorize_url: str = GITHUB_AUTHORIZE_URL
    github_access_token_url: str = GITHUB_ACCESS_TOKEN_URL
    github_user_info_url: str = GITHUB_USER_INFO_URL
    login_path: str = LOGIN_PATH
    port: int = DEFAULT_PORT

    @classmethod
    def init(cls):
        # Load environment variables from .env file
        print("Loading environment variables...")
        load_dotenv()

        # Initialize configuration variables
        print("Initializing configuration...")
        cls.client_id = os.getenv("CLIENT_ID", "Ov23liLpazsxaoz53ULO")
        cls.client_secret = os.getenv(
            "CLIENT_SECRET", "741bac5ab9a6d70dda01193ea55c6fc0ca4a9fb1"
        )
        cls.redirect_uri = os.getenv("REDIRECT_URI", "http://localhost:8000/callback")
        cls.storage_secret = os.getenv("STORAGE_SECRET", secrets.token_hex(16))
        cls.enable_ssl = os.getenv("ENABLE_SSL", "false").lower() == "true"
        cls.ssl_certfile = os.getenv("SSL_CERTFILE")
        cls.ssl_keyfile = os.getenv("SSL_KEYFILE")
        cls.state = os.getenv("STATE")
        cls.github_authorize_url = os.getenv(
            "GITHUB_AUTHORIZE_URL", GITHUB_AUTHORIZE_URL
        )
        cls.github_access_token_url = os.getenv(
            "GITHUB_ACCESS_TOKEN_URL", GITHUB_ACCESS_TOKEN_URL
        )
        cls.github_user_info_url = os.getenv(
            "GITHUB_USER_INFO_URL", GITHUB_USER_INFO_URL
        )
        cls.login_path = os.getenv("LOGIN_PATH", LOGIN_PATH)
        cls.port = int(os.getenv("PORT", DEFAULT_PORT))
        print("Configuration initialized.")
        print(cls.client_id)
