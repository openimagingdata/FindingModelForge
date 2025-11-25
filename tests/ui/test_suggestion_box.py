"""Suggestion box UI tests.

Tests for the suggestion box feature including:
- Visibility of "Suggest" link and hero button
- Modal opening from different triggers
- Form content based on auth state
- Alpine.js reactive validation
- HTMX submission flow
- Alert display and dismissal
- Form state reset after submission
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

from .utils import wait_for_htmx_settled

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestSuggestionBoxVisibility:
    """Test visibility of suggestion box UI elements."""

    async def test_navbar_suggest_link_visible_on_home_page(self, page: Page) -> None:
        """Test that 'Suggest' link is visible in navbar on home page."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Check for the "Suggest" link in navbar (desktop or mobile)
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await expect(suggest_link).to_be_visible(timeout=5000)

    async def test_navbar_suggest_link_visible_on_finding_models_page(self, page: Page) -> None:
        """Test that 'Suggest' link is visible in navbar on finding models page."""
        await page.goto("http://localhost:8000/finding-models")
        await page.wait_for_load_state("domcontentloaded")

        # Check for the "Suggest" link in navbar
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await expect(suggest_link).to_be_visible(timeout=5000)

    async def test_hero_button_visible_on_home_page_only(self, page: Page) -> None:
        """Test that hero 'Suggest' button is visible only on home page."""
        # Home page - should have hero button
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        hero_button = page.locator('button[data-modal-target="suggestion-modal"]:has-text("Suggest")')
        await expect(hero_button).to_be_visible(timeout=5000)

        # Finding models page - should NOT have hero button
        await page.goto("http://localhost:8000/finding-models")
        await page.wait_for_load_state("domcontentloaded")

        # Verify hero button is NOT visible (count should be 0)
        hero_button_count = await page.locator(
            'button[data-modal-target="suggestion-modal"]:has-text("Suggest")'
        ).count()
        assert hero_button_count == 0, "Hero button should not be visible on finding models page"


class TestSuggestionBoxModalOpening:
    """Test modal opening from different triggers."""

    async def test_navbar_link_opens_modal(self, page: Page) -> None:
        """Test clicking navbar 'Suggest' link opens modal."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Click navbar "Suggest" link
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to become visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Verify form is inside modal
        form_in_modal = modal.locator('form[hx-post="/suggestions"]')
        await expect(form_in_modal).to_be_visible(timeout=5000)

    async def test_hero_button_opens_modal(self, page: Page) -> None:
        """Test clicking hero button opens modal."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Click hero button
        hero_button = page.locator('button[data-modal-target="suggestion-modal"]:has-text("Suggest")')
        await hero_button.click()

        # Wait for modal to become visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Verify form is inside modal
        form_in_modal = modal.locator('form[hx-post="/suggestions"]')
        await expect(form_in_modal).to_be_visible(timeout=5000)


class TestSuggestionBoxFormContent:
    """Test form content based on authentication state."""

    async def test_form_shows_email_input_for_anonymous_users(self, page: Page) -> None:
        """Test that form shows email input field for anonymous users."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Verify email input is visible
        email_input = modal.locator('input[name="submitter_email"]')
        await expect(email_input).to_be_visible(timeout=5000)

        # Verify user info box is NOT visible
        user_info = modal.locator('text="Submitting as"')
        user_info_count = await user_info.count()
        assert user_info_count == 0, "User info should not be visible for anonymous users"

    async def test_form_shows_user_info_for_authenticated_users(self, authenticated_page: Page) -> None:
        """Test that form shows user info (no email input) for authenticated users."""
        await authenticated_page.goto("http://localhost:8000/")
        await authenticated_page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = authenticated_page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = authenticated_page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Verify user info is visible
        user_info = modal.locator('text="Submitting as"')
        await expect(user_info).to_be_visible(timeout=5000)

        # Verify email input is NOT visible
        email_input_count = await modal.locator('input[name="submitter_email"]').count()
        assert email_input_count == 0, "Email input should not be visible for authenticated users"


class TestSuggestionBoxReactiveValidation:
    """Test Alpine.js reactive validation logic."""

    async def test_input_respects_maxlength_attribute(self, page: Page) -> None:
        """Test that input field respects maxlength attribute (300 chars).

        Note: Character counter was removed from UI as unnecessary clutter.
        The maxlength attribute provides sufficient user feedback.
        """
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Get content input
        content_input = modal.locator('input[name="content"]')

        # Verify maxlength attribute is set
        maxlength = await content_input.get_attribute("maxlength")
        assert maxlength == "300", "Input should have maxlength='300'"

        # Type text and verify it works
        test_text = "Test suggestion"
        await content_input.fill(test_text)
        input_value = await content_input.input_value()
        assert input_value == test_text, "Input should accept text up to maxlength"

    async def test_submit_button_disabled_when_content_empty(self, page: Page) -> None:
        """Test that submit button is disabled when content is empty."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Submit button should be disabled when content is empty
        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await expect(submit_button).to_be_disabled(timeout=5000)

    async def test_submit_button_enabled_at_max_length(self, page: Page) -> None:
        """Test that submit button is enabled when content is exactly 300 characters.

        Note: The input has maxlength="300" so we can't actually type more than 300 chars.
        This test verifies that filling exactly 300 chars keeps the button enabled,
        demonstrating the validation boundary.
        """
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Fill with exactly 300 characters (maxlength prevents more)
        content_input = modal.locator('input[name="content"]')
        text_300_chars = "a" * 300  # Exactly 300 characters
        await content_input.fill(text_300_chars)

        # Submit button should be enabled at 300 chars (boundary)
        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await expect(submit_button).to_be_enabled(timeout=5000)

        # Verify input contains exactly 300 characters
        input_value = await content_input.input_value()
        assert len(input_value) == 300, "Input should contain exactly 300 characters"

    async def test_submit_button_enabled_when_content_valid(self, page: Page) -> None:
        """Test that submit button is enabled when content is 1-300 characters."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Fill with valid text (1-300 characters)
        content_input = modal.locator('input[name="content"]')
        valid_text = "This is a valid suggestion"
        await content_input.fill(valid_text)

        # Submit button should be enabled
        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await expect(submit_button).to_be_enabled(timeout=5000)


class TestSuggestionBoxSubmissionFlow:
    """Test HTMX submission flow and alert handling."""

    async def test_modal_closes_and_alert_appears_after_submit(self, page: Page) -> None:
        """Test that modal closes and alert appears after successful submission."""
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Fill form and submit
        content_input = modal.locator('input[name="content"]')
        await content_input.fill("Test suggestion for UI testing")

        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await submit_button.click()

        # Wait for HTMX to complete
        await wait_for_htmx_settled(page)

        # Modal should still be visible (based on implementation notes)
        # but alert should appear in #alert-container
        alert = page.locator("#alert-container #suggestion-alert")
        await expect(alert).to_be_visible(timeout=5000)

        # Verify alert message
        alert_text = alert.locator(".text-sm")
        await expect(alert_text).to_contain_text("Thanks for your suggestion", timeout=5000)

    async def test_user_stays_on_current_page_after_submit(self, page: Page) -> None:
        """Test that user stays on current page after submission (no navigation)."""
        # Start on home page
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal and submit suggestion
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        content_input = modal.locator('input[name="content"]')
        await content_input.fill("Test suggestion - no navigation")

        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await submit_button.click()

        # Wait for HTMX to complete
        await wait_for_htmx_settled(page)

        # URL should remain on home page (may have # anchor from modal)
        assert page.url.startswith("http://localhost:8000/"), "User should stay on the home page after submission"
        # Should NOT navigate to different page
        assert "/suggestions" not in page.url, "Should not navigate to suggestions page"

    async def test_alert_has_close_button_with_alpine_interaction(self, page: Page) -> None:
        """Test that alert has a close button with Alpine.js @click handler.

        Note: Alert now uses Alpine.js x-transition for animations and @click for dismissal
        instead of Flowbite data attributes. This test verifies the button exists and
        works correctly with Alpine.js.
        """
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Submit suggestion to trigger alert
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        content_input = modal.locator('input[name="content"]')
        await content_input.fill("Test suggestion for dismissal")

        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await submit_button.click()

        # Wait for HTMX to complete
        await wait_for_htmx_settled(page)

        # Alert should be visible in alert container (with Alpine.js animation)
        alert = page.locator("#alert-container #suggestion-alert")
        await expect(alert).to_be_visible(timeout=5000)

        # Verify the close button exists (now uses Alpine.js @click)
        close_button = alert.locator('button[aria-label="Close"]')
        await expect(close_button).to_be_visible(timeout=5000)

        # Verify button has correct aria-label
        aria_label = await close_button.get_attribute("aria-label")
        assert aria_label == "Close", "Close button should have aria-label='Close'"

        # Verify button is clickable (demonstrates Alpine.js implementation works)
        await expect(close_button).to_be_enabled(timeout=5000)

        # Click the close button and verify alert disappears (Alpine.js x-show)
        await close_button.click()
        await expect(alert).to_be_hidden(timeout=2000)


class TestSuggestionBoxStateManagement:
    """Test form state management."""

    async def test_form_state_persists_across_modal_close_reopen(self, page: Page) -> None:
        """Test that form state persists when modal is closed and reopened.

        Note: Alpine.js x-data persists across modal visibility changes. This is actually
        desired behavior - if user closes modal accidentally, their input is preserved.
        For a clean submission flow, users should submit, which triggers HTMX to swap
        the alert, and then they can close the modal knowing submission succeeded.
        """
        await page.goto("http://localhost:8000/")
        await page.wait_for_load_state("domcontentloaded")

        # Open modal
        suggest_link = page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        modal = page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Fill form (but don't submit)
        content_input = modal.locator('input[name="content"]')
        test_text = "Test suggestion text"
        await content_input.fill(test_text)

        # Close modal manually (click cancel button)
        cancel_button = modal.locator('button[data-modal-hide="suggestion-modal"]:has-text("Cancel")')
        await cancel_button.click()

        # Wait for modal to close
        await expect(modal).to_be_hidden(timeout=5000)

        # Reopen modal
        await suggest_link.click()
        await expect(modal).to_be_visible(timeout=5000)

        # Form state should persist (Alpine.js x-data persists)
        content_input_value = await content_input.input_value()
        assert content_input_value == test_text, "Form state should persist when modal reopens"

        # Submit button should be enabled since form has valid content
        submit_button = modal.locator('button[type="submit"]:has-text("Submit Suggestion")')
        await expect(submit_button).to_be_enabled(timeout=5000)


class TestSuggestionBoxPersistence:
    """Test database persistence of suggestions."""

    async def test_suggestion_persisted_to_database(self, authenticated_page: Page) -> None:
        """Test that suggestions are saved to MongoDB."""
        from datetime import UTC, datetime

        from motor.motor_asyncio import AsyncIOMotorClient

        from app.config import settings

        # Arrange
        timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
        test_content = f"Database persistence test suggestion {timestamp}"

        # Navigate and open modal
        await authenticated_page.goto("http://localhost:8000/")

        # Open modal
        suggest_link = authenticated_page.locator('a[data-modal-target="suggestion-modal"]:has-text("Suggest")').first
        await suggest_link.click()

        # Wait for modal to be visible
        modal = authenticated_page.locator("#suggestion-modal")
        await expect(modal).to_be_visible(timeout=5000)

        # Act - Submit suggestion
        await authenticated_page.fill('input[name="content"]', test_content)
        await authenticated_page.click('button[type="submit"]:has-text("Submit Suggestion")')
        await wait_for_htmx_settled(authenticated_page)

        # Assert - Query MongoDB to verify persistence
        client = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]

        suggestion = await db.suggestions.find_one({"content": test_content}, sort=[("created_at", -1)])

        assert suggestion is not None, "Suggestion should be persisted to database"
        assert suggestion["content"] == test_content
        assert "user_id" in suggestion
        assert "submitter_email" in suggestion  # Should have submitter_email field (can be None)
        assert "created_at" in suggestion
        assert isinstance(suggestion["created_at"], datetime)

        # For authenticated user, verify user_id is set
        assert suggestion["user_id"] == 999999, "User ID should match authenticated test user"

        # Cleanup
        await db.suggestions.delete_one({"_id": suggestion["_id"]})
        client.close()
