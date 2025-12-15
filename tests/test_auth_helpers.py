"""Authentication helpers for Playwright tests."""

import os
from datetime import UTC, datetime, timedelta

from playwright.async_api import Page

# Base URL for tests - respects PORT environment variable (default: 8000)
BASE_URL = f"http://localhost:{os.environ.get('PORT', '8000')}"


class PlaywrightAuthHelper:
    """Helper class for handling authentication in Playwright tests."""

    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url

    async def create_test_user_session(self, page: Page) -> dict:
        """Create a test user session by mocking GitHub OAuth flow."""
        # This simulates what happens after GitHub OAuth success
        test_user_data = {
            "id": 123456,
            "login": "playwright-test-user",
            "email": "playwright@test.example.com",
            "name": "Playwright Test User",
            "avatar_url": "https://github.com/playwright-test-user.png",
            "organizations": ["test-org"],
        }

        # Method 1: Direct cookie injection (if we can generate valid JWT)
        await self.inject_auth_cookies(page, test_user_data)

        return test_user_data

    async def inject_auth_cookies(self, page: Page, user_data: dict) -> None:
        """Inject authentication cookies directly."""
        # For this approach, we'd need to generate a valid JWT token
        # This is a simplified version - in practice you'd need the actual JWT secret

        # Navigate to any page first to set the domain
        await page.goto(f"{self.base_url}/")

        # Option 1: Try to set localStorage (if the app uses it)
        await page.evaluate(f"""
            localStorage.setItem('auth_user', {user_data!r});
            localStorage.setItem('auth_token', 'mock-jwt-token');
        """)

        # Option 2: Set HTTP-only cookies (more realistic)
        await page.context.add_cookies(
            [
                {
                    "name": "access_token",
                    "value": "mock-jwt-access-token",
                    "domain": "localhost",
                    "path": "/",
                    "httpOnly": True,
                    "secure": False,  # False for localhost
                    "sameSite": "Lax",
                },
                {
                    "name": "refresh_token",
                    "value": "mock-jwt-refresh-token",
                    "domain": "localhost",
                    "path": "/",
                    "httpOnly": True,
                    "secure": False,
                    "sameSite": "Lax",
                },
            ]
        )

    async def login_via_oauth_mock(self, page: Page) -> None:
        """Mock the OAuth login flow by directly hitting auth endpoints."""
        # This would simulate the OAuth callback
        # You'd need to create a test endpoint that bypasses GitHub

        # Navigate to a mock auth endpoint that sets up the session
        await page.goto(f"{self.base_url}/auth/test-login")

    async def create_real_jwt_token(self, user_data: dict) -> str:
        """Create a real JWT token using the app's secret (for testing)."""
        # This requires access to the JWT secret and implementation
        # You'd import your JWT creation logic here
        import jwt

        # You'd need to get the actual secret from your app config
        secret = "your-test-secret-key"  # Should match your test environment

        payload = {
            "sub": str(user_data["id"]),
            "login": user_data["login"],
            "email": user_data["email"],
            "name": user_data["name"],
            "exp": datetime.now(UTC) + timedelta(hours=1),
            "iat": datetime.now(UTC),
        }

        token = jwt.encode(payload, secret, algorithm="HS256")
        return token


# Convenience functions for tests
async def setup_authenticated_page(page: Page) -> dict:
    """Set up an authenticated page with a test user."""
    auth_helper = PlaywrightAuthHelper()
    user_data = await auth_helper.create_test_user_session(page)
    return user_data


async def verify_authentication_works(page: Page) -> bool:
    """Verify that authentication is working by checking a protected route."""
    await page.goto(f"{BASE_URL}/create-finding-model")
    await page.wait_for_load_state("networkidle")

    # If authenticated, should NOT see login page
    title = await page.title()
    return "Login Required" not in title
