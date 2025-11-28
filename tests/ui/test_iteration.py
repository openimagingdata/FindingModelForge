"""UI tests for Model Iteration Feature (Sprint 1 MVP).

Tests the complete iteration workflow including:
- Iteration button visibility on published finding model pages
- Creating iteration drafts from published models
- Iteration draft UI (banner, form, vs normal edit form)
- Natural language iteration command submission
"""

from __future__ import annotations

import re

import pytest
from playwright.async_api import Page, expect

from .utils import (
    seed_iteration_result,
    wait_for_htmx_settled,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestIterationButtonVisibility:
    """Test iteration button display on finding model detail pages."""

    async def test_iterate_button_visible_for_authenticated_user(self, authenticated_page: Page) -> None:
        """Test that Create Iteration button appears for authenticated users on published model pages."""
        page = authenticated_page

        # Navigate to a published finding model detail page
        # Using abdominal-abscess which exists in the GitHub repository
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")

        # Wait for page to load
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        # Verify the "Create Iteration" button is visible for authenticated users
        iterate_button = page.locator('button:has-text("Create Iteration")')
        await expect(iterate_button).to_be_visible(timeout=5000)

        # Verify button has correct styling (purple theme)
        await expect(iterate_button).to_have_class(re.compile(r".*bg-purple-600.*"))

    async def test_iterate_button_not_visible_for_unauthenticated_user(self, page: Page) -> None:
        """Test that Create Iteration button is NOT visible for unauthenticated users."""
        # Navigate WITHOUT authentication
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")

        # Wait for page to load
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        # Verify the "Create Iteration" button is NOT visible
        iterate_button = page.locator('button:has-text("Create Iteration")')
        await expect(iterate_button).to_have_count(0)


class TestIterationDraftCreation:
    """Test creating iteration drafts from published models."""

    async def test_iterate_button_creates_draft_and_redirects(self, authenticated_page: Page) -> None:
        """Test clicking Create Iteration button creates draft and redirects to draft page."""
        page = authenticated_page

        # Navigate to finding model detail
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")

        # Wait for page to load
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        # Click "Create Iteration" button
        iterate_button = page.locator('button:has-text("Create Iteration")')
        await expect(iterate_button).to_be_visible(timeout=5000)
        await iterate_button.click()

        # Verify redirect to draft page (URL pattern: /drafts/{draft_id})
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Verify we're on a draft page
        draft_url = page.url
        assert "/drafts/" in draft_url, f"Expected draft URL, got: {draft_url}"

        # Verify the iteration draft page is displayed with iteration UI
        # The iteration banner should be visible (text: "Iteration Draft:")
        iteration_banner = page.locator('div[role="alert"]:has-text("Iteration Draft")')
        await expect(iteration_banner).to_be_visible(timeout=10000)


class TestIterationDraftUI:
    """Test iteration draft page UI elements."""

    async def test_iteration_form_visible_on_iteration_draft(self, authenticated_page: Page) -> None:
        """Test that iteration draft shows iteration UI (banner + form) instead of normal edit form."""
        page = authenticated_page

        # First create an iteration draft by clicking the button
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()

        # Wait for redirect to draft page
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Verify iteration banner is displayed
        iteration_banner = page.locator('div[role="alert"]:has-text("Iteration Draft")')
        await expect(iteration_banner).to_be_visible(timeout=10000)

        # Verify the iteration form (textarea + submit button) is visible
        iteration_textarea = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea).to_be_visible(timeout=5000)

        # Verify "Apply Changes" button is visible
        apply_button = page.locator('button:has-text("Apply Changes")')
        await expect(apply_button).to_be_visible()

        # Verify the normal edit form is NOT visible
        # Normal edit form has description textarea
        description_textarea = page.locator('textarea[name="description"]')
        await expect(description_textarea).to_have_count(0)

    async def test_iteration_results_container_visible(self, authenticated_page: Page) -> None:
        """Test that iteration results container is present on iteration draft page."""
        page = authenticated_page

        # Create iteration draft
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Verify iteration results placeholder is shown initially
        placeholder_text = page.locator('p:has-text("Your changes will appear here")')
        await expect(placeholder_text).to_be_visible(timeout=5000)

    async def test_iteration_json_preview_visible(self, authenticated_page: Page) -> None:
        """Test that current model JSON preview is shown on iteration draft page."""
        page = authenticated_page

        # Create iteration draft
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # JSON accordion should have heading for "Current Model JSON"
        json_heading = page.locator('button:has-text("Current Model JSON")')
        await expect(json_heading).to_be_visible(timeout=5000)


class TestIterationFormSubmission:
    """Test iteration form submission and response handling."""

    async def test_iteration_form_submission_with_mocked_response(self, authenticated_page: Page) -> None:
        """Test submitting iteration command (uses test-auth mock for AI response)."""
        page = authenticated_page

        # Create iteration draft
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Wait for iteration form to be ready
        iteration_textarea = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea).to_be_visible(timeout=5000)

        # Enter natural language command
        test_command = "Add a new attribute called 'Severity' with values 'Mild', 'Moderate', and 'Severe'"
        await iteration_textarea.fill(test_command)

        # Verify "Apply Changes" button is enabled when text is entered
        apply_button = page.locator('button:has-text("Apply Changes")')
        await expect(apply_button).to_be_enabled()

        # Submit the form
        await apply_button.click()

        # Wait for HTMX to process the request
        await wait_for_htmx_settled(page, timeout=30000)

        # For test user (999999), the AI service returns mocked responses
        # The result should show EITHER:
        # 1. Success message with changes/rejections, OR
        # 2. Error message if AI service failed
        # We just verify that the placeholder is gone (indicating something was returned)
        placeholder_text = page.locator('text="Your changes will appear here after you apply them"')
        await expect(placeholder_text).to_have_count(0)

    async def test_iteration_form_submit_button_disabled_when_empty(self, authenticated_page: Page) -> None:
        """Test that Apply Changes button is disabled when textarea is empty."""
        page = authenticated_page

        # Create iteration draft
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Wait for iteration form to be ready
        iteration_textarea = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea).to_be_visible(timeout=5000)

        # Verify button is disabled when textarea is empty
        apply_button = page.locator('button:has-text("Apply Changes")')
        await expect(apply_button).to_be_disabled()

        # Enter some text
        await iteration_textarea.fill("Add attribute")
        await expect(apply_button).to_be_enabled()

        # Clear the text
        await iteration_textarea.fill("")
        await expect(apply_button).to_be_disabled()


class TestIterationWorkflow:
    """Test complete iteration workflow scenarios."""

    async def test_multiple_iteration_commands_on_same_draft(self, authenticated_page: Page) -> None:
        """Test submitting multiple iteration commands to the same draft.

        After each iteration, user is redirected to view mode to see results.
        To make another iteration, user must click Edit to return to edit mode.
        """
        page = authenticated_page

        # Create iteration draft
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Capture draft URL for later navigation
        draft_url = page.url

        # First iteration command
        iteration_textarea = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea).to_be_visible(timeout=5000)
        await iteration_textarea.fill("Add severity attribute")

        apply_button = page.locator('button:has-text("Apply Changes")')
        await apply_button.click()

        # After successful iteration, HX-Redirect takes us to view mode
        # AI service can take ~40-60 seconds, so we need a longer timeout
        await page.wait_for_url(re.compile(r".*/drafts/.*\?mode=view"), timeout=90000)

        # Verify we're in view mode - "Changes Applied" banner should be visible
        changes_banner = page.locator('text="Changes Applied:"')
        await expect(changes_banner).to_be_visible(timeout=10000)

        # To make another iteration, navigate back to edit mode
        await page.goto(draft_url)  # draft_url has mode=edit

        # Verify iteration form is visible again for another iteration
        iteration_textarea_reload = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea_reload).to_be_visible(timeout=10000)
        await expect(iteration_textarea_reload).to_be_enabled(timeout=5000)

        # Submit second iteration command
        await iteration_textarea_reload.fill("Add location attribute")

        apply_button_reload = page.locator('button:has-text("Apply Changes")')
        await apply_button_reload.click()

        # After second iteration, redirected to view mode again
        # AI service can take ~40-60 seconds
        await page.wait_for_url(re.compile(r".*/drafts/.*\?mode=view"), timeout=90000)

        # Verify "Changes Applied" banner visible after second iteration
        await expect(changes_banner).to_be_visible(timeout=10000)

    async def test_iteration_draft_persists_across_sessions(self, authenticated_page: Page) -> None:
        """Test that iteration draft can be accessed again after creation."""
        page = authenticated_page

        # Create iteration draft and capture the draft ID
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        iterate_button = page.locator('button:has-text("Create Iteration")')
        await iterate_button.click()
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Extract draft ID from URL
        draft_url = page.url
        draft_id = draft_url.split("/drafts/")[1].split("?")[0]

        # Verify iteration UI is visible
        iteration_banner = page.locator('div[role="alert"]:has-text("Iteration Draft")')
        await expect(iteration_banner).to_be_visible(timeout=5000)

        # Navigate away
        await page.goto("http://localhost:8000/")

        # Navigate back to the same draft
        await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=edit")

        # Verify iteration UI is still visible
        iteration_banner_after = page.locator('div[role="alert"]:has-text("Iteration Draft")')
        await expect(iteration_banner_after).to_be_visible(timeout=10000)

        # Verify iteration form is still there
        iteration_textarea = page.locator('textarea[placeholder*="Example"]')
        await expect(iteration_textarea).to_be_visible()


class TestIterationResultsDisplay:
    """Test iteration results display with changes and rejections.

    These tests use the proper pattern:
    1. Navigate to a real published finding model
    2. Click "Create Iteration" to create a proper iteration draft via backend
    3. Extract draft ID from URL
    4. Seed iteration result into Redis
    5. Navigate to view mode and verify display
    """

    async def _create_iteration_draft(self, page: Page) -> str:
        """Helper to create an iteration draft via UI and return its ID."""
        # Navigate to finding model
        await page.goto("http://localhost:8000/finding-models/abdominal-abscess")
        await expect(
            page.locator("h1, h2").filter(has_text=re.compile(r"abdominal abscess", re.IGNORECASE))
        ).to_be_visible(timeout=10000)

        # Click "Create Iteration" button
        iterate_button = page.locator('button:has-text("Create Iteration")')
        await expect(iterate_button).to_be_visible(timeout=5000)
        await iterate_button.click()

        # Wait for redirect to draft page
        await page.wait_for_url("**/drafts/**", timeout=10000)

        # Extract draft ID from URL
        draft_url = page.url
        draft_id = draft_url.split("/drafts/")[1].split("?")[0]
        return draft_id

    async def test_iteration_results_with_both_changes_and_rejections(self, authenticated_page: Page) -> None:
        """Test that iteration results show BOTH changes (green) AND rejections (yellow).

        When an iteration has both successful changes AND some requests that couldn't
        be applied, both should be displayed to the user.
        """
        page = authenticated_page

        # Create iteration draft via the UI (proper flow)
        draft_id = await self._create_iteration_draft(page)

        # Seed an iteration result with BOTH changes AND rejections
        await seed_iteration_result(
            draft_id=draft_id,
            changes=[
                "Added new attribute 'Severity' with values Mild, Moderate, Severe",
                "Updated description to include severity classification",
            ],
            rejections=[
                "Cannot remove 'Presence' attribute - it is required by the schema",
                "Value 'Unknown' already exists on the 'Presence' attribute",
            ],
            success=True,
        )

        # Navigate to the draft in VIEW mode (where results are displayed)
        await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=view")

        # Wait for page to load
        await expect(page.locator("h1, h2").first).to_be_visible(timeout=10000)

        # Verify the "Changes Applied" banner (green) is visible
        changes_banner = page.locator('text="Changes Applied:"')
        await expect(changes_banner).to_be_visible(timeout=5000)

        # Verify at least one of the changes is listed (use partial match)
        change_text = page.locator('li:has-text("Added new attribute")')
        await expect(change_text.first).to_be_visible(timeout=5000)

        # Verify the "Some changes were rejected" banner (yellow) is visible
        rejections_banner = page.locator('text="Some changes were rejected:"')
        await expect(rejections_banner).to_be_visible(timeout=5000)

        # Verify at least one of the rejections is listed (use partial match)
        rejection_text = page.locator('li:has-text("Cannot remove")')
        await expect(rejection_text.first).to_be_visible(timeout=5000)

    async def test_iteration_results_with_only_changes(self, authenticated_page: Page) -> None:
        """Test that iteration results show only changes when no rejections."""
        page = authenticated_page

        # Create iteration draft via the UI (proper flow)
        draft_id = await self._create_iteration_draft(page)

        # Seed an iteration result with changes only (no rejections)
        await seed_iteration_result(
            draft_id=draft_id,
            changes=[
                "Added new attribute 'Location' with anatomical regions",
                "Added synonym 'nodule'",
            ],
            rejections=[],  # No rejections
            success=True,
        )

        # Navigate to the draft in VIEW mode
        await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=view")

        # Wait for page to load
        await expect(page.locator("h1, h2").first).to_be_visible(timeout=10000)

        # Verify the "Changes Applied" banner is visible
        changes_banner = page.locator('text="Changes Applied:"')
        await expect(changes_banner).to_be_visible(timeout=5000)

        # Verify changes are listed (use partial match)
        change_text = page.locator('li:has-text("Added new attribute")')
        await expect(change_text.first).to_be_visible(timeout=5000)

        # Verify the rejections banner is NOT visible (no rejections)
        rejections_banner = page.locator('text="Some changes were rejected:"')
        await expect(rejections_banner).to_have_count(0)

    async def test_iteration_results_with_only_rejections(self, authenticated_page: Page) -> None:
        """Test that iteration results handle the edge case of only rejections."""
        page = authenticated_page

        # Create iteration draft via the UI (proper flow)
        draft_id = await self._create_iteration_draft(page)

        # Seed an iteration result with rejections only (no changes made)
        await seed_iteration_result(
            draft_id=draft_id,
            changes=[],  # No changes
            rejections=[
                "Cannot delete the only attribute",
                "Invalid attribute type specified",
            ],
            success=True,  # Still "successful" in terms of processing, just no changes
        )

        # Navigate to the draft in VIEW mode
        await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=view")

        # Wait for page to load
        await expect(page.locator("h1, h2").first).to_be_visible(timeout=10000)

        # Verify the rejections banner is visible
        rejections_banner = page.locator('text="Some changes were rejected:"')
        await expect(rejections_banner).to_be_visible(timeout=5000)

        # Verify rejections are listed (use partial match)
        rejection_text = page.locator('li:has-text("Cannot delete")')
        await expect(rejection_text.first).to_be_visible(timeout=5000)

        # The changes banner should NOT appear when there are only rejections
        changes_banner = page.locator('text="Changes Applied:"')
        await expect(changes_banner).to_have_count(0)
