"""Shared fixtures for UI/Playwright tests."""

import os
from collections.abc import AsyncGenerator

import pytest
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from .utils import TEST_USER_ID, authenticate_user, cleanup_test_data, collect_console_errors


@pytest.fixture
async def browser() -> AsyncGenerator[Browser, None]:
    """Create a Playwright browser instance."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
        try:
            yield browser
        finally:
            await browser.close()


@pytest.fixture
async def context(browser: Browser) -> AsyncGenerator[BrowserContext, None]:
    """Create a browser context with UI test headers."""
    context = await browser.new_context(
        extra_http_headers={
            "X-UI-Test-Mode": "skip-ai"  # Skip AI operations in UI tests
        }
    )
    try:
        yield context
    finally:
        await context.close()


@pytest.fixture
async def page(context: BrowserContext) -> AsyncGenerator[Page, None]:
    """Create a page instance."""
    page = await context.new_page()
    try:
        yield page
    finally:
        await page.close()


@pytest.fixture
async def authenticated_page(page: Page) -> AsyncGenerator[Page, None]:
    """Create an authenticated page instance using test-auth."""
    await authenticate_user(page)
    yield page


@pytest.fixture
async def page_with_console_tracking(page: Page) -> AsyncGenerator[tuple[Page, list[str], list[str]], None]:
    """Create a page with console error/warning tracking."""
    errors, warnings = collect_console_errors(page)
    yield page, errors, warnings


@pytest.fixture
async def authenticated_page_with_console(
    page: Page,
) -> AsyncGenerator[tuple[Page, list[str], list[str]], None]:
    """Create an authenticated page with console tracking."""
    errors, warnings = collect_console_errors(page)
    await authenticate_user(page)
    yield page, errors, warnings


@pytest.fixture(autouse=True)
async def cleanup_test_user_data() -> AsyncGenerator[None, None]:
    """Automatically clean up test user data before and after each test."""
    # Cleanup before test
    await cleanup_test_data(TEST_USER_ID)

    yield

    # Cleanup after test
    await cleanup_test_data(TEST_USER_ID)


@pytest.fixture
def test_user_id() -> int:
    """Provide the test user ID."""
    return TEST_USER_ID


# @pytest.fixture(autouse=True) - REMOVED: Old mock fixture
# async def mock_ai_operations() -> AsyncGenerator[None, None]:
#     """Mock slow AI operations to prevent timeouts and improve test reliability.
#
#     This fixture automatically mocked the find_similar_models function, but
#     it doesn't work for browser-based tests since tests run in browser, not server.
#     Now using header-based approach with X-UI-Test-Mode: skip-ai header.
#     """
#     # This approach doesn't work for Playwright tests
#     pass
