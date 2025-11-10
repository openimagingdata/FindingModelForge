"""Profile page UI tests.

Tests for the Profile/My Forge page functionality including:
- Draft and submitted card display
- Card action buttons (View, Edit, Delete)
- Delete modal functionality
- Empty state handling
"""

from __future__ import annotations

import re

import pytest
from playwright.async_api import Page, expect

from .utils import (
    TEST_USER_ID,
    navigate_to_profile_page,
    seed_draft,
    seed_drafts,
    verify_no_console_errors,
    wait_for_htmx_settled,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestDraftCards:
    """Test draft and submitted card display and basic actions."""

    async def test_draft_and_submitted_cards_display(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that draft and submitted cards render with appropriate action buttons."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Draft"
        submitted_name = "UI Test Submitted"

        # Seed test data
        ids = await seed_drafts(user_id=TEST_USER_ID, draft_name=draft_name, submitted_name=submitted_name)
        submitted_id = ids["submitted_id"]

        # Navigate to profile page
        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Verify both cards are visible
        draft_card = page.locator(f".draft-card:has-text('{draft_name}')")
        submitted_card = page.locator(f".draft-card:has-text('{submitted_name}')")
        await expect(draft_card).to_be_visible()
        await expect(submitted_card).to_be_visible()

        # Submitted card should NOT have Delete or Edit buttons
        await expect(submitted_card.locator("a[title='Delete'], button[title='Delete']")).to_have_count(0)
        await expect(submitted_card.locator("a[title='Edit'], button[title='Edit']")).to_have_count(0)
        await expect(page.locator(f"#delete-draft-modal-{submitted_id}")).to_have_count(0)

        # Submitted card should have View button
        await expect(submitted_card.locator("a[title='View'], button[title='View']")).to_have_count(1)

        # Draft card should have Edit and Delete buttons
        await expect(draft_card.locator("a[title='Edit'], button[title='Edit']")).to_have_count(1)
        await expect(draft_card.locator("a[title='Delete'], button[title='Delete']")).to_have_count(1)

        # Verify no console errors
        await verify_no_console_errors(errors, warnings)

    async def test_view_submitted_shows_json(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that viewing a submitted draft shows JSON accordion and IDs."""
        page, errors, warnings = authenticated_page_with_console

        submitted_name = "UI Test View Submitted"
        await seed_drafts(user_id=TEST_USER_ID, draft_name="UI Test Draft", submitted_name=submitted_name)

        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Click View on submitted card
        submitted_card = page.locator(f".draft-card:has-text('{submitted_name}')")
        await submitted_card.locator("a[title='View'], button[title='View']").first.click()

        # Should show JSON accordion and IDs for submitted drafts
        await expect(page.locator("#finding-model-json")).to_be_visible(timeout=5000)
        await expect(page.locator("text=ID:")).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_view_draft_no_json(self, authenticated_page_with_console: tuple[Page, list[str], list[str]]) -> None:
        """Test that viewing an unsubmitted draft does not show JSON accordion."""
        page, errors, warnings = authenticated_page_with_console

        # Create a draft with generated JSON (but still status='draft')
        from .utils import generate_valid_generated_json

        draft_name = "UI Test Draft With JSON"
        gen_json = await generate_valid_generated_json(draft_name)

        await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            generated_json=gen_json,
            status="draft",  # Still draft status
        )

        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # View button MUST be visible for drafts with generated_json
        draft_card = page.locator(f".draft-card:has-text('{draft_name}')")
        view_button = draft_card.locator("a[title='View'], button[title='View']")
        await expect(view_button).to_be_visible(timeout=5000)
        await view_button.first.click()

        # JSON accordion should be absent for drafts (regardless of generated_json)
        await expect(page.locator("#finding-model-json")).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_edit_draft_navigation(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that clicking Edit navigates to unified draft page in edit mode."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Edit Navigation"
        await seed_draft(user_id=TEST_USER_ID, name=draft_name)

        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Click Edit on draft card
        draft_card = page.locator(f".draft-card:has-text('{draft_name}')")
        await draft_card.locator("a[title='Edit'], button[title='Edit']").first.click()

        # Should be on unified draft edit page
        await expect(page.locator("h1:has-text('Edit Finding Model Draft')")).to_be_visible(timeout=5000)
        await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible(timeout=5000)

        # Should have form fields
        await expect(page.locator("textarea#description")).to_be_visible()
        await expect(page.locator("textarea[name='attributes_markdown']")).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestDeleteModal:
    """Test delete modal functionality."""

    async def test_delete_draft_modal_and_removal(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that delete modal opens, confirms deletion, and removes card."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Delete"
        submitted_name = "UI Test Keep"

        ids = await seed_drafts(user_id=TEST_USER_ID, draft_name=draft_name, submitted_name=submitted_name)
        draft_id = ids["draft_id"]

        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Click Delete on draft card
        draft_card = page.locator(f".draft-card:has-text('{draft_name}')")
        await draft_card.locator("a[title='Delete'], button[title='Delete']").first.click()

        # Modal should appear
        modal = page.locator(f"#delete-draft-modal-{draft_id}")
        await expect(modal).to_be_visible(timeout=5000)

        # Confirm deletion
        await modal.locator("button:has-text('Yes, delete')").click()
        await wait_for_htmx_settled(page)  # Wait for HTMX OOB swap

        # After HTMX swap, the card should be removed
        await expect(page.locator(f"#draft-card-{draft_id}")).to_have_count(0)

        # No-drafts placeholder should remain hidden because submitted still exists
        await expect(page.locator("#no-drafts")).to_have_class(re.compile(r".*\bhidden\b.*"))

        # Submitted card should still be visible
        submitted_card = page.locator(f".draft-card:has-text('{submitted_name}')")
        await expect(submitted_card).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestEmptyState:
    """Test empty state handling when no drafts exist."""

    async def test_delete_last_draft_shows_placeholder(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that deleting the last draft shows the 'no drafts' placeholder."""
        page, errors, warnings = authenticated_page_with_console

        only_draft_name = "UI Test Only Draft"
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=only_draft_name)

        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Delete the only draft
        card = page.locator(f"#drafts-grid .draft-card:has-text('{only_draft_name}')")
        await expect(card).to_be_visible()
        await card.locator("a[title='Delete'], button[title='Delete']").first.click()

        modal = page.locator(f"#delete-draft-modal-{draft_id}")
        await expect(modal).to_be_visible(timeout=5000)
        await modal.locator("button:has-text('Yes, delete')").click()
        await wait_for_htmx_settled(page)  # Wait for HTMX OOB swap

        # Card should be removed and placeholder should show
        await expect(page.locator(f"#draft-card-{draft_id}")).to_have_count(0)
        await expect(page.locator("#no-drafts")).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestProfileNavigation:
    """Test navigation to and from the profile page."""

    async def test_profile_page_loads(self, authenticated_page_with_console: tuple[Page, list[str], list[str]]) -> None:
        """Test that the profile page loads correctly."""
        page, errors, warnings = authenticated_page_with_console

        await navigate_to_profile_page(page)

        # Check for key profile page elements - either drafts grid or no-drafts placeholder
        # Since this test doesn't create any drafts, we should expect the no-drafts element
        await expect(page.locator("#no-drafts")).to_be_visible(timeout=5000)

        # Title should indicate this is the profile/My Forge page
        title = await page.title()
        assert "My Forge" in title or "Profile" in title

        await verify_no_console_errors(errors, warnings)

    async def test_navigation_between_profile_and_draft_edit(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test navigation from profile to draft edit and back."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Navigation"
        await seed_draft(user_id=TEST_USER_ID, name=draft_name)

        # Start at profile
        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=5000)

        # Navigate to edit
        draft_card = page.locator(f".draft-card:has-text('{draft_name}')")
        await draft_card.locator("a[title='Edit'], button[title='Edit']").first.click()

        # Verify we're on edit page
        await expect(page.locator("h1:has-text('Edit Finding Model Draft')")).to_be_visible(timeout=5000)

        # Navigate back to profile
        await page.go_back()
        await page.wait_for_selector("#drafts-grid")

        # Should be back on profile
        await expect(page.locator("#drafts-grid")).to_be_visible()
        await expect(draft_card).to_be_visible()

        await verify_no_console_errors(errors, warnings)
