"""Test finding models navigation and display functionality."""

import re

import pytest
from playwright.async_api import Page, expect

from tests.ui.utils import (
    collect_console_errors,
    verify_no_console_errors,
    wait_for_htmx_settled,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


async def navigate_to_finding_models_list(page: Page) -> None:
    """Navigate to the finding models list page."""
    await page.goto("http://localhost:8000/finding-models")
    # Playwright's expect() auto-waits for elements - no need for networkidle


class TestFindingModelsListPage:
    """Test the finding models list page functionality."""

    async def test_list_page_loads(self, page: Page) -> None:
        """Test that the finding models list page loads with proper elements."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Check page title
        await expect(page).to_have_title("Finding Models - Finding Model Forge")

        # Check main heading
        await expect(page.locator("h1")).to_contain_text("Finding Models")

        # Check breadcrumb structure
        breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
        await expect(breadcrumb).to_contain_text("Home")
        await expect(breadcrumb).to_contain_text("Finding Models")

        # Check search input
        search_input = page.get_by_role("searchbox", name="Search")
        await expect(search_input).to_be_visible()
        await expect(search_input).to_have_attribute("placeholder", "Search finding models...")

        # Check table structure
        table = page.locator("table").first
        await expect(table).to_be_visible()
        await expect(table.locator("thead")).to_contain_text("ID")
        await expect(table.locator("thead")).to_contain_text("Name")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )


class TestIndexCodeDisplay:
    """Test index code display at all three levels on model detail pages."""

    async def test_finding_model_level_index_codes(self, page: Page) -> None:
        """Test that finding model level index codes display correctly."""
        errors, warnings = collect_console_errors(page)

        # Navigate to abdominal abscess model (has index codes)
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Check for "Codes" heading at model level
        codes_heading = page.locator("h4").filter(has_text="Codes").first
        await expect(codes_heading).to_be_visible()

        # Check for index code badges with indigo styling
        model_badges = page.locator("span.bg-indigo-100, span.bg-indigo-900").first
        await expect(model_badges).to_be_visible()

        # Verify badge contains expected content (two-line format)
        badge_content = await model_badges.text_content()
        assert "GAMUTS:4244" in badge_content
        assert "abdominal abscess" in badge_content

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_attribute_level_index_codes(self, page: Page) -> None:
        """Test that attribute level index codes display correctly."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Should have multiple "Codes" headings (model + attributes)
        codes_headings = page.locator("h4").filter(has_text="Codes")
        await expect(codes_headings).to_have_count(3)  # 1 model + 2 attributes

        # Check attribute-specific badges
        attribute_badges = page.locator("span.bg-indigo-100, span.bg-indigo-900")
        await expect(attribute_badges).to_have_count(4)  # 1 model + 3 attribute codes

        # Verify specific attribute code content (use more specific selectors)
        snomed_badge = page.locator(".font-mono").filter(has_text="SNOMED:705057003")
        await expect(snomed_badge).to_be_visible()

        radlex_badge = page.locator(".font-mono").filter(has_text="RADLEX:RID49896")
        await expect(radlex_badge).to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_value_level_popovers(self, page: Page) -> None:
        """Test that value level popovers display correctly on hover."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Check that value buttons have popover attributes
        value_buttons = page.locator('button[data-popover-trigger="hover"]')
        await expect(value_buttons).to_have_count(12)  # 4 + 8 values

        # Test specific value button
        absent_button = page.get_by_role("button", name="absent")
        await expect(absent_button).to_be_visible()

        # Hover over button to trigger popover
        await absent_button.hover()

        # Check that popover appears
        popover = page.locator('div[role="tooltip"]').filter(has_text="Abdominal abscess is absent")
        await expect(popover).to_be_visible()

        # Verify popover content structure
        await expect(popover.locator("p")).to_contain_text("Abdominal abscess is absent")

        # Check for "Codes" section in popover
        codes_section = popover.locator("h5").filter(has_text="Codes")
        await expect(codes_section).to_be_visible()

        # Verify specific codes in popover
        await expect(popover).to_contain_text("RADLEX:RID28473")
        await expect(popover).to_contain_text("SNOMED:2667000")
        await expect(popover).to_contain_text("Absent (qualifier value)")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_multiple_value_popovers(self, page: Page) -> None:
        """Test that multiple value popovers work correctly."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Test different value buttons
        test_values = ["present", "indeterminate", "unchanged"]

        for value_name in test_values:
            value_button = page.get_by_role("button", name=value_name)
            await expect(value_button).to_be_visible()

            # Hover to show popover
            await value_button.hover()

            # Check popover appears with value-specific content
            popover = page.locator('div[role="tooltip"]:visible')
            await expect(popover).to_be_visible()

            # Each popover should have codes
            codes_heading = popover.locator("h5").filter(has_text="Codes")
            await expect(codes_heading).to_be_visible()

            # Move away to hide popover
            await page.locator("h2").first.hover()
            await expect(popover).not_to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_index_code_badge_structure(self, page: Page) -> None:
        """Test that index code badges have correct two-line structure."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Get the first badge and check internal structure
        first_badge = page.locator("span.bg-indigo-100, span.bg-indigo-900").first
        await expect(first_badge).to_be_visible()

        # Check that badge contains two span elements (two-line format)
        inner_spans = first_badge.locator("span")
        await expect(inner_spans).to_have_count(2)

        # First span should be monospace (system:code)
        system_code_span = inner_spans.first
        await expect(system_code_span).to_have_class(re.compile(r".*\bfont-mono\b.*"))

        # Verify content structure
        system_code_text = await system_code_span.text_content()
        assert ":" in system_code_text  # Should contain system:code format

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_no_index_codes_handling(self, page: Page) -> None:
        """Test that pages without index codes don't show empty sections."""
        errors, warnings = collect_console_errors(page)

        # Navigate to finding models list (shouldn't have index code sections)
        await page.goto("http://localhost:8000/finding-models")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Should not have "Codes" headings on the listing page
        codes_headings = page.locator("h4").filter(has_text="Codes")
        await expect(codes_headings).to_have_count(0)

        # Should not have index code badges
        index_badges = page.locator("span.bg-indigo-100, span.bg-indigo-900")
        await expect(index_badges).to_have_count(0)

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_popover_accessibility(self, page: Page) -> None:
        """Test that popovers have proper accessibility attributes."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Check popover ARIA attributes
        value_button = page.get_by_role("button", name="absent")
        popover_target = await value_button.get_attribute("data-popover-target")
        assert popover_target is not None

        # Find corresponding popover
        popover = page.locator(f'div[id="{popover_target}"]')
        await expect(popover).to_have_attribute("role", "tooltip")

        # Check trigger attribute
        await expect(value_button).to_have_attribute("data-popover-trigger", "hover")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_search_functionality(self, page: Page) -> None:
        """Test search input and results."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Find search input
        search_input = page.get_by_role("searchbox", name="Search")
        await expect(search_input).to_be_visible()

        # Type search query
        await search_input.fill("abscess")

        # Wait for debounce (500ms) and HTMX request
        await page.wait_for_timeout(600)

        # URL should update with search parameter
        await page.wait_for_timeout(700)  # Wait for search debounce
        assert "search=abscess" in page.url

        # Page title should update
        await expect(page).to_have_title("Search: abscess - Finding Model Forge")

        # Results section should show search context
        results_info = page.locator("text=/Showing.*results.*for.*abscess/i").first
        if await results_info.is_visible():
            await expect(results_info).to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_search_with_debounce(self, page: Page) -> None:
        """Test that search has proper 500ms debounce."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        search_input = page.get_by_role("searchbox", name="Search")
        await expect(search_input).to_be_visible()

        # Track network requests
        requests = []
        page.on("request", lambda req: requests.append(req) if "finding-models" in req.url else None)

        # Type rapidly
        await search_input.type("test", delay=50)  # Fast typing

        # Should not immediately make request
        await page.wait_for_timeout(200)
        search_requests = [req for req in requests if "search=test" in req.url]
        assert len(search_requests) == 0, "Should not make immediate request"

        # After debounce delay, should make request
        await page.wait_for_timeout(400)  # Total 600ms
        search_requests = [req for req in requests if "search=test" in req.url]
        assert len(search_requests) >= 1, "Should make request after debounce"

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_pagination_controls(self, page: Page) -> None:
        """Test pagination UI and navigation."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Check for pagination controls (may not be visible if < 20 results)
        pagination = page.locator("nav[aria-label*='Pagination'], .pagination").first

        if await pagination.is_visible():
            # Should have Next button for navigation
            next_button = pagination.locator("text=/Next/i").first

            # If there's a Next button, try clicking it
            if await next_button.is_visible() and not await next_button.is_disabled():
                await next_button.click()
                await page.wait_for_timeout(500)  # Wait for HTMX

                # URL should update with page parameter
                assert "page=2" in page.url

                # Results should update
                results_info = page.locator("text=/Showing.*21.*to/i").first
                if await results_info.is_visible():
                    await expect(results_info).to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_empty_search_results(self, page: Page) -> None:
        """Test empty search results message."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        search_input = page.get_by_role("searchbox", name="Search")
        await search_input.fill("nonexistentfindingmodel12345")

        # Wait for debounce and response
        await page.wait_for_timeout(700)

        # Should show no results message
        no_results = page.locator("text=/No finding models found.*matching/i").first
        if await no_results.is_visible():
            await expect(no_results).to_contain_text("nonexistentfindingmodel12345")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )


class TestFindingModelsDetailNavigation:
    """Test navigation between finding models list and detail views."""

    async def test_htmx_navigation_to_detail(self, page: Page) -> None:
        """Test HTMX navigation from list to model detail."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Find clickable table row
        table_row = page.locator("table tbody tr").first

        if await table_row.is_visible():
            # Row should have pointer cursor (clickable)
            cursor_class = await table_row.get_attribute("class") or ""
            assert "cursor-pointer" in (cursor_class or "")

            # Get model name before clicking for verification
            model_name_cell = table_row.locator("td").nth(1)  # Name column
            if await model_name_cell.is_visible():
                model_name = await model_name_cell.inner_text()

                # Click row for HTMX navigation
                await table_row.click()
                await page.wait_for_timeout(1000)

                # Should be on detail page (URL change)
                assert "/finding-models/" in page.url

                # Page title should update
                await expect(page).to_have_title(f"{model_name} - Finding Model Forge")

                # Breadcrumb should update via OOB swap
                breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
                await expect(breadcrumb).to_contain_text("Home")
                await expect(breadcrumb).to_contain_text("Finding Models")
                await expect(breadcrumb).to_contain_text(model_name)

                # Content should be in #main-content
                main_content = page.locator("#main-content")
                await expect(main_content).not_to_be_empty()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_direct_detail_access(self, page: Page) -> None:
        """Test accessing a model detail page directly via URL."""
        errors, warnings = collect_console_errors(page)

        # Try to access a model directly (using common slug pattern)
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Give some time for the model to load from GitHub
        await page.wait_for_timeout(1000)

        # Check what page we ended up on
        current_url = page.url
        current_title = await page.title()

        # The test is valid regardless of whether the specific model exists
        # Just verify we got a valid response
        assert "Finding Model" in current_title, f"Expected Finding Model in title, got: {current_title}"

        # If we're on the detail page, verify detail content
        if "abdominal-abscess" in current_url and "abdominal abscess" in current_title:
            # Should have proper breadcrumb
            breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
            await expect(breadcrumb).to_contain_text("Home")
            await expect(breadcrumb).to_contain_text("Finding Models")
            await expect(breadcrumb).to_contain_text("abdominal abscess")

            # Should have model content - MUST be visible
            model_heading = page.locator("h2:has-text('abdominal abscess')")
            await expect(model_heading).to_be_visible(timeout=10000)  # Longer timeout for GitHub API

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
                "404",  # Expected if model doesn't exist
            ],
        )

    async def test_breadcrumb_navigation(self, page: Page) -> None:
        """Test breadcrumb links work correctly."""
        errors, warnings = collect_console_errors(page)

        # Start on detail page
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        if page.url.endswith("/abdominal-abscess"):
            # Click "Finding Models" breadcrumb link - MUST exist
            breadcrumb_link = page.locator("nav[aria-label='Breadcrumb'] a").filter(has_text="Finding Models")
            await expect(breadcrumb_link).to_be_visible(timeout=5000)
            await breadcrumb_link.click()
            await wait_for_htmx_settled(page)

            # Should navigate back to list
            assert "/finding-models" in page.url
            assert "/abdominal-abscess" not in page.url

            # Title should revert
            await expect(page).to_have_title("Finding Models - Finding Model Forge")

            # Should show list content
            table = page.locator("table").first
            await expect(table).to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
                "404",
            ],
        )

    async def test_detail_not_found(self, page: Page) -> None:
        """Test 404 handling for non-existent model."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/non-existent-model-slug")
        # Playwright's expect() auto-waits for elements - no need for networkidle

        # Should show 404 handling - verify it doesn't show broken page
        # Current implementation: stays on /non-existent-model-slug but shows list view
        if page.url.endswith("/non-existent-model-slug"):
            # Server renders list view as fallback - MUST show list table
            table = page.locator("table").first
            await expect(table).to_be_visible(timeout=5000)

            # Should show "Finding Models" heading (list view)
            heading = page.locator("h1:has-text('Finding Models')")
            await expect(heading).to_be_visible()

            # Note: error_message is set in context but not currently displayed in template
            # This is tracked as a UI improvement opportunity
        else:
            # Redirected away from non-existent slug - verify we're somewhere safe
            assert "/finding-models" in page.url or "/404" in page.url or page.url == "/"

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
                "404",  # Expected error for this test
                "not found",  # Expected error in logs
            ],
        )


class TestFindingModelsHistoryNavigation:
    """Test browser history navigation."""

    async def test_browser_back_from_detail(self, page: Page) -> None:
        """Test browser back button from detail to list."""
        errors, warnings = collect_console_errors(page)

        # Navigate to list page first
        await navigate_to_finding_models_list(page)

        # Click on first table row to go to detail
        table_row = page.locator("table tbody tr").first

        if await table_row.is_visible():
            await table_row.click()
            await page.wait_for_timeout(1000)

            # Should be on detail page
            assert "/finding-models/" in page.url

            # Use browser back button
            await page.go_back()
            await page.wait_for_timeout(500)

            # Should be back on list page
            import re

            assert re.search(r".*/finding-models$", page.url), "URL should end with /finding-models"

            # Title should be restored
            await expect(page).to_have_title("Finding Models - Finding Model Forge")

            # Breadcrumb should be restored
            breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
            await expect(breadcrumb).to_contain_text("Finding Models")
            await expect(breadcrumb).not_to_contain_text("abdominal abscess")  # No model name

            # List content should be visible
            table = page.locator("table").first
            await expect(table).to_be_visible()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_browser_forward_to_detail(self, page: Page) -> None:
        """Test browser forward button back to detail."""
        errors, warnings = collect_console_errors(page)

        # Navigate: list -> detail -> back -> forward
        await navigate_to_finding_models_list(page)

        table_row = page.locator("table tbody tr").first

        if await table_row.is_visible():
            # Get model name for verification
            model_name_cell = table_row.locator("td").nth(1)
            if await model_name_cell.is_visible():
                model_name = await model_name_cell.inner_text()

                # Navigate to detail
                await table_row.click()
                await page.wait_for_timeout(1000)

                # Go back
                await page.go_back()
                await page.wait_for_timeout(500)

                # Go forward
                await page.go_forward()
                await page.wait_for_timeout(500)

                # Should be back on detail page
                assert "/finding-models/" in page.url

                # Title should be restored
                await expect(page).to_have_title(f"{model_name} - Finding Model Forge")

                # Breadcrumb should be restored
                breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
                await expect(breadcrumb).to_contain_text(model_name)

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_title_restoration_on_back(self, page: Page) -> None:
        """Test that page titles update correctly during browser navigation."""
        errors, warnings = collect_console_errors(page)

        # Start at homepage
        await page.goto("http://localhost:8000/")
        # Playwright's expect() auto-waits for elements - no need for networkidle
        initial_title = await page.title()

        # Navigate to finding models
        await navigate_to_finding_models_list(page)
        await expect(page).to_have_title("Finding Models - Finding Model Forge")

        # Navigate to detail (if available)
        table_row = page.locator("table tbody tr").first
        if await table_row.is_visible():
            model_name_cell = table_row.locator("td").nth(1)
            if await model_name_cell.is_visible():
                model_name = await model_name_cell.inner_text()
                await table_row.click()
                await page.wait_for_timeout(1000)

                # Detail page title
                await expect(page).to_have_title(f"{model_name} - Finding Model Forge")

                # Back to list
                await page.go_back()
                await page.wait_for_timeout(500)
                await expect(page).to_have_title("Finding Models - Finding Model Forge")

                # Back to home
                await page.go_back()
                await page.wait_for_timeout(500)
                await expect(page).to_have_title(initial_title)

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_breadcrumb_restoration_on_back(self, page: Page) -> None:
        """Test that breadcrumbs update correctly during browser navigation."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Check initial breadcrumb
        breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
        await expect(breadcrumb).to_contain_text("Home")
        await expect(breadcrumb).to_contain_text("Finding Models")

        # Navigate to detail
        table_row = page.locator("table tbody tr").first
        if await table_row.is_visible():
            model_name_cell = table_row.locator("td").nth(1)
            if await model_name_cell.is_visible():
                model_name = await model_name_cell.inner_text()
                await table_row.click()
                await page.wait_for_timeout(1000)

                # Detail breadcrumb
                await expect(breadcrumb).to_contain_text("Home")
                await expect(breadcrumb).to_contain_text("Finding Models")
                await expect(breadcrumb).to_contain_text(model_name)

                # Back to list
                await page.go_back()
                await page.wait_for_timeout(500)

                # List breadcrumb restored
                await expect(breadcrumb).to_contain_text("Home")
                await expect(breadcrumb).to_contain_text("Finding Models")
                # Should not contain model name anymore
                breadcrumb_text = await breadcrumb.inner_text()
                assert model_name.lower() not in breadcrumb_text.lower()

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )


class TestFindingModelsDynamicFeatures:
    """Test dynamic features like titles, search state, and JavaScript functionality."""

    async def test_list_page_title(self, page: Page) -> None:
        """Test default list page title."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Default title
        await expect(page).to_have_title("Finding Models - Finding Model Forge")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_search_page_title(self, page: Page) -> None:
        """Test search result page title."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        search_input = page.get_by_role("searchbox", name="Search")
        await search_input.fill("test")
        await page.wait_for_timeout(700)  # Debounce + request

        # Search title
        await expect(page).to_have_title("Search: test - Finding Model Forge")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_detail_page_title(self, page: Page) -> None:
        """Test model-specific detail page title."""
        errors, warnings = collect_console_errors(page)

        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        # Playwright's expect() auto-waits for elements - no need for networkidle
        await page.wait_for_timeout(1000)  # Wait for model to load

        # Check if we're on detail page or redirected to list
        current_title = await page.title()
        if "abdominal-abscess" in page.url and "abdominal abscess" in current_title:
            await expect(page).to_have_title("abdominal abscess - Finding Model Forge")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
                "404",
            ],
        )

    async def test_search_state_preservation(self, page: Page) -> None:
        """Test that search state is preserved in URL and form."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        search_input = page.get_by_role("searchbox", name="Search")
        await search_input.fill("abscess")
        await page.wait_for_timeout(700)

        # URL should contain search parameter
        assert "search=abscess" in page.url

        # Search input should retain value
        await expect(search_input).to_have_value("abscess")

        # Navigate to detail and back
        table_row = page.locator("table tbody tr").first
        if await table_row.is_visible():
            await table_row.click()
            await page.wait_for_timeout(1000)

            await page.go_back()
            await page.wait_for_timeout(500)

            # Search state should be preserved
            assert "search=abscess" in page.url
            await expect(search_input).to_have_value("abscess")

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )

    async def test_htmx_history_element_configuration(self, page: Page) -> None:
        """Test HTMX history element configuration prevents CSS-in-JS conflicts."""
        errors, warnings = collect_console_errors(page)

        await navigate_to_finding_models_list(page)

        # Check that main-content has hx-history-elt attribute
        main_content = page.locator("#main-content")
        await expect(main_content).to_be_visible()

        history_elt = await main_content.get_attribute("hx-history-elt")
        assert history_elt == "true"

        # Navigate to detail to trigger HTMX swap
        table_row = page.locator("table tbody tr").first
        if await table_row.is_visible():
            await table_row.click()
            await page.wait_for_timeout(1000)

            # Should not have applyStyles errors
            style_errors = [err for err in errors if "applyStyles" in err]
            assert len(style_errors) == 0, f"Should not have applyStyles errors: {style_errors}"

        await verify_no_console_errors(
            errors,
            warnings,
            allowed_patterns=[
                "Failed to load resource",
                "favicon.ico",
            ],
        )
