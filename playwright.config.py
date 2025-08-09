"""Playwright configuration for FindingModelForge integration tests."""

from typing import Any


def pytest_configure(config: Any) -> None:
    """Configure Playwright for pytest."""
    # This will be called by pytest-playwright
    _ = config  # Mark as used to avoid linting warnings


# Playwright configuration
class PlaywrightConfig:
    """Configuration for Playwright browser tests."""

    # Browser configuration
    BROWSER = "chromium"
    HEADLESS = True
    SLOW_MO = 100  # Milliseconds between actions

    # Page configuration
    VIEWPORT = {"width": 1280, "height": 720}
    IGNORE_HTTPS_ERRORS = True

    # Test configuration
    TIMEOUT = 30000  # 30 seconds
    EXPECT_TIMEOUT = 10000  # 10 seconds

    # Base URLs for different environments
    BASE_URLS = {
        "development": "http://localhost:8000",
        "test": "http://localhost:8001",
        "staging": "https://staging.findingmodelforge.com",
    }

    @classmethod
    def get_base_url(cls, env: str = "development") -> str:
        """Get base URL for the specified environment."""
        return cls.BASE_URLS.get(env, cls.BASE_URLS["development"])


# Export configuration for pytest-playwright
PLAYWRIGHT_CONFIG = PlaywrightConfig()
