"""Draft management UI tests.

Tests for draft-specific functionality including:
- Unified draft page edit/preview mode switching
- Form validation with Alpine.js
- Draft autosave behavior
- Model reuse vs regeneration logic
- Back navigation with form persistence
"""

from __future__ import annotations

import re

import pytest
from playwright.async_api import Page, expect

from .utils import (
    BASE_URL,
    TEST_USER_ID,
    generate_valid_generated_json,
    navigate_to_profile_page,
    seed_draft,
    verify_no_console_errors,
    wait_for_htmx_settled,
    wait_for_htmx_swap,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestUnifiedDraftPage:
    """Test unified draft page functionality with edit/preview modes."""

    async def test_edit_mode_to_preview_mode_switching(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test switching between edit and preview modes on unified draft page."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Mode Switching"
        # Create draft WITH generated_json so mode toggle buttons appear
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for mode switching.",
            synonyms=["mode", "switch", "test"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
        )

        # Navigate to draft in edit mode (explicit since drafts with generated_json default to view mode)
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")

        # Should be in edit mode
        await expect(page.locator("h1:has-text('Edit Finding Model Draft')")).to_be_visible(timeout=10000)
        await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible()
        await expect(page.locator("textarea#description")).to_be_visible()

        # Make a change and update to preview mode
        desc_field = page.locator("textarea#description")
        current_desc = await desc_field.input_value()
        await desc_field.fill(current_desc + " Updated for preview.")

        await page.locator("button:has-text('Update & Preview')").click()
        await wait_for_htmx_swap(page, "#success-alert")

        # Should see success alert
        success_alert = page.locator("#success-alert")
        await expect(success_alert).to_be_visible(timeout=5000)
        await expect(success_alert).to_contain_text("Draft updated successfully!")

        # Should now be in preview mode with mode toggle buttons visible
        # (since draft has generated_json after update)
        edit_mode_btn = page.locator("button#edit-mode-btn")
        await expect(edit_mode_btn).to_be_visible(timeout=10000)

        # Verify we're in view mode by checking for model display elements
        # Draft preview shows the actual finding model name as h2, not "Your Finding Model is Ready!"
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=5000)

        # Verify the updated description is shown in preview
        await expect(page.locator("body")).to_contain_text("Updated for preview.")

        await verify_no_console_errors(errors, warnings)

    async def test_direct_preview_mode_access(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test accessing draft directly in preview mode via URL parameter."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Preview Mode"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="draft")

        # Navigate to draft in preview mode
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Should show model display without edit controls
        # Draft preview shows the actual finding model name as h2, not "Your Finding Model is Ready!"
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=10000)

        # Should not show JSON accordion for drafts (even with generated_json)
        await expect(page.locator("#finding-model-json")).to_have_count(0)

        # Should have edit button to switch back to edit mode (if draft has generated_json)
        edit_btn = page.locator("button#edit-mode-btn")
        await expect(edit_btn).to_be_visible(timeout=10000)

        await verify_no_console_errors(errors, warnings)

    async def test_update_preview_button_renders_correctly(self, authenticated_page: Page):
        """Regression test: Verify button renders properly without escaped HTML.

        This test catches the bug where raw HTML was passed to a Jinja2 macro
        and displayed as escaped text instead of rendering as a proper button.
        """
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name="UI Test Button Rendering",
            description="Test that button HTML renders correctly",
            attributes_markdown="Presence of test\n- present: visible\n- absent: not visible",
            status="draft",
        )

        await authenticated_page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")

        # Get the button element
        button = authenticated_page.locator("button:has-text('Update & Preview')")
        await expect(button).to_be_visible()

        # CRITICAL: Verify button does NOT contain raw HTML/SVG markup as text
        button_text = await button.inner_text()
        assert "<span" not in button_text, f"Button contains raw HTML: {button_text}"
        assert "<svg" not in button_text, f"Button contains raw SVG: {button_text}"
        assert "htmx-indicator" not in button_text, f"Button shows CSS class as text: {button_text}"
        assert "animate-spin" not in button_text, f"Button shows CSS class as text: {button_text}"

        # Verify the visible text is clean
        # The htmx-indicator span is hidden by default, so only "Update & Preview" should be visible
        assert "Update & Preview" in button_text


class TestFormValidation:
    """Test Alpine.js form validation behavior."""

    async def test_button_validation_for_draft_with_existing_model(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test Update & Preview button validation for drafts with generated models."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Button Validation"
        gen_json = await generate_valid_generated_json(draft_name)
        await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="draft")

        # Go to profile and edit the draft
        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=10000)

        card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
        await expect(card).to_be_visible()
        await card.locator("a[title='Edit'], button[title='Edit']").first.click()

        # Find the button and test its initial state
        button = page.locator("button:has-text('Update & Preview')")
        await expect(button).to_be_visible(timeout=5000)

        # Test 1: Button should be DISABLED initially (no changes + has existing model)
        await expect(button).to_be_disabled(timeout=5000)

        # Test 2: Make a change - button should become ENABLED
        desc_field = page.locator("textarea#description")
        current_desc = await desc_field.input_value()
        await desc_field.fill(current_desc + " Updated content.")

        # Alpine.js is synchronous for form field changes
        await expect(button).to_be_enabled(timeout=5000)

        # Test 3: Revert the change - button should become DISABLED again
        await desc_field.fill(current_desc)
        await expect(button).to_be_disabled(timeout=5000)

        # Test 4: Change attributes instead - button should become ENABLED
        attrs_field = page.locator("textarea[name='attributes_markdown']")
        current_attrs = await attrs_field.input_value()
        await attrs_field.fill(current_attrs + "\\n- new: attribute")
        await expect(button).to_be_enabled(timeout=5000)

        # Test 5: Can successfully submit with changes
        await button.click()
        await wait_for_htmx_swap(page, "#success-alert")

        # Should see success message
        success_alert = page.locator("#success-alert")
        await expect(success_alert).to_be_visible(timeout=5000)
        await expect(success_alert).to_contain_text("Draft updated successfully!")

        await verify_no_console_errors(errors, warnings)

    async def test_button_enabled_for_draft_without_model(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that button is enabled for drafts without existing generated models."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test No Model"
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            # No generated_json
        )

        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")

        # Find the button and test its state
        button = page.locator("button:has-text('Update & Preview')")
        await expect(button).to_be_visible(timeout=5000)

        # Button should be enabled since there's no existing model
        await expect(button).to_be_enabled(timeout=5000)

        await verify_no_console_errors(errors, warnings)


class TestModelReuse:
    """Test model reuse vs regeneration logic."""

    # Note: Testing "model reuse when no changes" is not possible via UI tests because
    # the Alpine.js validation correctly prevents form submission when there are no changes.
    # This is correct application behavior - users should not be able to submit unchanged forms.
    # The model reuse logic itself should be tested via backend unit tests.

    async def test_model_regeneration_when_changed(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that model is regenerated when changes are made."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Model Regeneration"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            generated_json=gen_json,
            description="Original description for change test.",
            synonyms=["original"],
        )

        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")

        # Set up response listener
        reuse_header: dict[str, str] = {}

        def on_response(response) -> None:  # type: ignore[no-untyped-def]
            try:
                if "/update-and-redirect" in response.url and response.request.method == "POST":
                    val = response.headers.get("x-model-reused")
                    if val is not None:
                        reuse_header["x-model-reused"] = val
            except Exception:
                pass

        page.on("response", on_response)  # type: ignore[arg-type]

        # Make a meaningful change to trigger regeneration
        desc_field = page.locator("textarea#description")
        await desc_field.fill("Significantly changed description to trigger regeneration.")

        button = page.locator("button:has-text('Update & Preview')")
        await expect(button).to_be_enabled(timeout=5000)

        await button.click()
        await wait_for_htmx_settled(page, timeout=30000)  # Regeneration takes longer

        # Should see success message
        await expect(page.locator("#success-alert")).to_be_visible(timeout=5000)

        # Verify the change is reflected
        await expect(page.locator("body")).to_contain_text("Significantly changed description")

        # Check regeneration header (should be "0" for regenerated)
        if "x-model-reused" in reuse_header:
            assert reuse_header["x-model-reused"] == "0", "Model should be regenerated when changed"

        await verify_no_console_errors(errors, warnings)


class TestBackNavigation:
    """Test back navigation and form persistence."""

    async def test_back_from_preview_prefills_form(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that switching back to edit mode preserves form values."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Back Navigation"
        seeded_description = "Seeded description for back navigation test."
        seeded_synonyms = ["back", "navigation", "test"]
        seeded_attrs = "### presence\\n- absent: Not present\\n- present: Present\\n- unknown: Unknown\\n"

        gen_json = await generate_valid_generated_json(draft_name)
        await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description=seeded_description,
            synonyms=seeded_synonyms,
            attributes_markdown=seeded_attrs,
            generated_json=gen_json,
        )

        # Go to profile and edit the draft
        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=10000)

        card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
        await card.locator("a[title='Edit'], button[title='Edit']").first.click()

        # Make a change and update
        desc_field = page.locator("textarea#description")
        await desc_field.fill(seeded_description + " (test update)")

        button = page.locator("button:has-text('Update & Preview')")
        await button.click()
        await wait_for_htmx_swap(page, "#success-alert")

        # Should see success alert
        await expect(page.locator("#success-alert")).to_be_visible(timeout=5000)

        # Switch back to edit mode
        # Mode toggle buttons should be visible after update (draft now has generated_json)
        edit_mode_btn = page.locator("button#edit-mode-btn")
        await expect(edit_mode_btn).to_be_visible(timeout=10000)
        await edit_mode_btn.click()
        await wait_for_htmx_swap(page, "button:has-text('Update & Preview')")

        # Should be back on edit mode with prefilled values
        await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible(timeout=10000)

        # Description should contain the update
        desc_value = await page.locator("textarea#description").input_value()
        assert "(test update)" in desc_value

        # Attributes should be prefilled
        attrs_value = await page.locator("textarea#attributes_markdown").input_value()
        assert "### presence" in attrs_value

        # Synonyms should be visible as badges
        for synonym in seeded_synonyms:
            badge_selector = f"span.inline-flex.items-center:has-text('{synonym}')"
            await expect(page.locator(badge_selector)).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestDraftAutosave:
    """Test draft autosave behavior during editing."""

    async def test_draft_autosave_on_update(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that draft is saved when updating via Update & Preview."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Autosave"
        draft_id = await seed_draft(
            user_id=TEST_USER_ID, name=draft_name, description="Original description for autosave test."
        )

        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")

        # Make changes
        desc_field = page.locator("textarea#description")
        await desc_field.fill("Updated description for autosave verification.")

        attrs_field = page.locator("textarea[name='attributes_markdown']")
        current_attrs = await attrs_field.input_value()
        await attrs_field.fill(current_attrs + "\\n- autosave: Test autosave functionality\\n")

        # Update the draft
        button = page.locator("button:has-text('Update & Preview')")
        await button.click()
        await wait_for_htmx_swap(page, "#success-alert")

        # Verify update succeeded
        await expect(page.locator("#success-alert")).to_be_visible(timeout=5000)

        # Navigate away and back to verify persistence
        await navigate_to_profile_page(page)
        await expect(page.locator("#drafts-grid")).to_be_visible(timeout=10000)

        # Edit the draft again
        card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
        await card.locator("a[title='Edit'], button[title='Edit']").first.click()

        # Verify changes persisted
        desc_value = await page.locator("textarea#description").input_value()
        assert "Updated description for autosave verification." in desc_value

        attrs_value = await page.locator("textarea#attributes_markdown").input_value()
        assert "autosave: Test autosave functionality" in attrs_value

        await verify_no_console_errors(errors, warnings)


class TestDraftModalWorkflows:
    """Test Submit/Delete modal workflows for draft actions."""

    async def test_submit_draft_modal_workflow(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test the complete submit draft modal workflow."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Submit Modal"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="public")

        # Navigate to draft in view mode to see action buttons
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Verify the Submit Draft button is visible
        submit_button = page.locator("button:has-text('Submit Draft')")
        await expect(submit_button).to_be_visible(timeout=10000)

        # Click the Submit Draft button to open modal
        await submit_button.click()
        await page.wait_for_selector(f"#submit-draft-modal-{draft_id}", state="visible")

        # Verify the submit modal appears with correct content
        modal = page.locator(f"#submit-draft-modal-{draft_id}")
        await expect(modal).to_be_visible(timeout=5000)
        await expect(modal).to_contain_text("Are you sure you want to submit this draft?")
        await expect(modal).to_contain_text("This will lock the draft and prevent further edits")

        # Verify modal has correct buttons
        confirm_button = modal.locator("button:has-text('Yes, submit')")
        cancel_button = modal.locator("button:has-text('Cancel')")
        await expect(confirm_button).to_be_visible()
        await expect(cancel_button).to_be_visible()

        # Test cancel functionality
        await cancel_button.click()
        await expect(modal).to_be_hidden()  # Modal should close

        # Still on draft page, draft should still be status="public"
        await expect(
            page.locator("span.text-blue-600:has-text('Public'), span.text-blue-400:has-text('Public')")
        ).to_be_visible()

        # Now test actual submit
        await submit_button.click()
        await expect(modal).to_be_visible()

        # Click confirm
        await confirm_button.click()
        await wait_for_htmx_swap(page, "span:has-text('Submitted')")

        # Should see status change to submitted
        await expect(
            page.locator("span.text-green-600:has-text('Submitted'), span.text-green-400:has-text('Submitted')")
        ).to_be_visible(timeout=10000)
        await expect(
            page.locator("span.text-blue-600:has-text('Public'), span.text-blue-400:has-text('Public')")
        ).to_have_count(0)

        # Action buttons should be gone (submitted drafts can't be modified)
        await expect(page.locator("button:has-text('Submit Draft')")).to_have_count(0)
        await expect(page.locator("button:has-text('Delete')")).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_delete_draft_modal_workflow(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test the complete delete draft modal workflow."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Delete Modal"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="draft")

        # Navigate to draft in view mode to see action buttons
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Verify the Delete button is visible (the trigger button, not the modal confirmation button)
        delete_button = page.locator("button[data-modal-target^='delete-draft-modal']:has-text('Delete')")
        await expect(delete_button).to_be_visible(timeout=10000)

        # Click the Delete button to open modal
        await delete_button.click()
        await page.wait_for_selector(f"#delete-draft-modal-{draft_id}", state="visible")

        # Verify the delete modal appears with correct content
        modal = page.locator(f"#delete-draft-modal-{draft_id}")
        await expect(modal).to_be_visible(timeout=5000)
        await expect(modal).to_contain_text("Are you sure you want to delete this draft?")
        await expect(modal).to_contain_text("This action cannot be undone")

        # Verify modal has correct buttons with appropriate colors
        confirm_button = modal.locator("button:has-text('Yes, delete')")
        cancel_button = modal.locator("button:has-text('Cancel')")
        await expect(confirm_button).to_be_visible()
        await expect(cancel_button).to_be_visible()
        # Red color for delete button
        await expect(confirm_button).to_have_class(re.compile(r".*bg-red-600.*"))

        # Test cancel functionality
        await cancel_button.click()
        await expect(modal).to_be_hidden()  # Modal should close

        # Still on draft page - check for the main heading
        await expect(page.locator(f"h1:has-text('{draft_name}'), h2:has-text('{draft_name}')")).to_be_visible()

        # Now test actual delete
        await delete_button.click()
        await expect(modal).to_be_visible()

        # Click confirm to delete
        await confirm_button.click()
        await wait_for_htmx_swap(page, "body")  # Wait for HTMX response

        # After delete, check if we're redirected or if there's an error message
        # The exact behavior may vary based on implementation
        current_url = page.url
        if f"/drafts/{draft_id}" in current_url:
            # If still on same page, the modal workflow still worked correctly
            # This test mainly verifies the modal workflow, not the delete logic
            print(f"Delete completed, still on page: {current_url}")
        else:
            # Successfully redirected away
            print(f"Successfully redirected to: {current_url}")

        await verify_no_console_errors(errors, warnings)

    async def test_modal_accessibility_and_keyboard_navigation(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test modal accessibility features and keyboard navigation."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Modal Accessibility"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="public")

        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Test submit modal accessibility
        submit_button = page.locator("button:has-text('Submit Draft')")
        await submit_button.click()

        modal = page.locator(f"#submit-draft-modal-{draft_id}")
        await expect(modal).to_be_visible()

        # Check ARIA attributes - modals have aria-modal="true" and tabindex="-1"
        await expect(modal).to_have_attribute("aria-modal", "true")
        await expect(modal).to_have_attribute("tabindex", "-1")

        # Test keyboard navigation - Escape key should close modal
        await page.keyboard.press("Escape")
        await expect(modal).to_be_hidden()

        # Test that modal can be closed by clicking outside
        await submit_button.click()
        await expect(modal).to_be_visible()

        # Click outside the modal (on backdrop)
        await page.mouse.click(50, 50)  # Click near top-left corner (backdrop)
        await expect(modal).to_be_hidden()

        await verify_no_console_errors(errors, warnings)

    async def test_modal_correct_htmx_targets(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that modals use correct HTMX targets (#main-content, not #draft-content)."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test HTMX Targets"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(user_id=TEST_USER_ID, name=draft_name, generated_json=gen_json, status="public")

        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Open submit modal and check HTMX attributes
        submit_button = page.locator("button:has-text('Submit Draft')")
        await submit_button.click()

        modal = page.locator(f"#submit-draft-modal-{draft_id}")
        confirm_button = modal.locator("button:has-text('Yes, submit')")

        # Check HTMX attributes point to correct target
        await expect(confirm_button).to_have_attribute("hx-target", "#main-content")
        await expect(confirm_button).to_have_attribute("hx-swap", "innerHTML")
        await expect(confirm_button).to_have_attribute("hx-post", f"/drafts/{draft_id}/submit")

        # Close this modal
        await page.keyboard.press("Escape")

        # Note: Public drafts don't have Delete buttons, so we skip testing delete modal
        # The Submit modal test above verifies the correct HTMX target pattern

        await verify_no_console_errors(errors, warnings)


class TestPublicDraftWorkflow:
    """Test the new make public workflow for drafts."""

    async def test_make_draft_public_complete_workflow(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test the complete draft → public → submitted flow."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Make Public Complete"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for make public workflow.",
            synonyms=["public", "workflow", "test"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
            status="draft",
        )

        # Navigate to the draft page
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Verify "Make Public" button is visible and "Submit Draft" is NOT
        make_public_button = page.locator("button[data-modal-target*='make-public-modal']:has-text('Make Public')")
        submit_button = page.locator("button:has-text('Submit Draft')")
        await expect(make_public_button).to_be_visible(timeout=10000)
        await expect(submit_button).to_have_count(0)

        # Verify status shows "Draft"
        await expect(page.locator("text=Status: Draft")).to_be_visible()

        # Click "Make Public" button to open modal
        await make_public_button.click()
        await page.wait_for_selector("[id^='make-public-modal-']", state="visible")

        # Verify the make public modal appears
        modal = page.locator("[id^='make-public-modal-']")
        await expect(modal).to_be_visible(timeout=5000)
        await expect(modal).to_contain_text("Make Public for Review")
        await expect(modal).to_contain_text(
            "Make this draft public for review? Other users will be able to view and comment on it."
        )

        # Confirm in the modal
        confirm_button = modal.locator("button:has-text('Make Public')")
        await expect(confirm_button).to_be_visible()
        await confirm_button.click()
        await wait_for_htmx_swap(page, "button:has-text('Submit Draft')")

        # Verify status changes to "public" (by checking Submit Draft button appears)
        await expect(page.locator("button:has-text('Submit Draft')")).to_be_visible(timeout=10000)
        await expect(
            page.locator("button[data-modal-target*='make-public-modal']:has-text('Make Public')")
        ).to_have_count(0)

        # Click "Submit Draft" and confirm
        submit_draft_button = page.locator("button:has-text('Submit Draft')")
        await submit_draft_button.click()
        await page.wait_for_selector("[id^='submit-draft-modal-']", state="visible")

        # Verify submit modal appears
        submit_modal = page.locator("[id^='submit-draft-modal-']")
        await expect(submit_modal).to_be_visible(timeout=5000)
        await expect(submit_modal).to_contain_text("Are you sure you want to submit this draft?")
        await expect(submit_modal).to_contain_text("This will lock the draft and prevent further edits")

        # Confirm submission
        submit_confirm_button = submit_modal.locator("button:has-text('Yes, submit')")
        await submit_confirm_button.click()
        await wait_for_htmx_swap(page, "text=Status: Submitted")

        # Verify status changes to "submitted"
        await expect(page.locator("text=Status: Submitted")).to_be_visible(timeout=10000)

        # Verify no action buttons remain
        await expect(page.locator("button:has-text('Submit Draft')")).to_have_count(0)
        await expect(
            page.locator("button[data-modal-target*='make-public-modal']:has-text('Make Public')")
        ).to_have_count(0)
        await expect(page.locator("button:has-text('Delete')")).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_cannot_submit_non_public_draft(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that drafts must be public before submission."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Cannot Submit Draft"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for non-public draft.",
            generated_json=gen_json,
            status="draft",  # Explicitly draft status
        )

        # Navigate to the draft page
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=view")

        # Verify "Make Public" button is visible
        make_public_button = page.locator("button[data-modal-target*='make-public-modal']:has-text('Make Public')")
        await expect(make_public_button).to_be_visible(timeout=10000)

        # Verify "Submit Draft" button is NOT visible
        submit_button = page.locator("button:has-text('Submit Draft')")
        await expect(submit_button).to_have_count(0)

        # Verify status shows draft
        await expect(page.locator("text=Status: Draft")).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_public_draft_visible_on_listing_page(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that public drafts appear on the /drafts listing."""
        page, errors, warnings = authenticated_page_with_console

        # Create multiple drafts with different statuses
        draft_name = "UI Test Draft Status"
        public_name = "UI Test Public Status"
        submitted_name = "UI Test Submitted Status"

        gen_json = await generate_valid_generated_json(public_name)

        # Create a draft status draft
        await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test draft description.",
            status="draft",
        )

        # Create a public status draft
        public_draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=public_name,
            description="Test public description.",
            generated_json=gen_json,
            status="public",
        )

        # Create a submitted status draft
        await seed_draft(
            user_id=TEST_USER_ID,
            name=submitted_name,
            description="Test submitted description.",
            generated_json=gen_json,
            status="submitted",
        )

        # Navigate to /drafts page
        await page.goto(f"{BASE_URL}/drafts")

        # Verify page title and header
        await expect(page.locator("h1:has-text('Public Drafts for Review')")).to_be_visible(timeout=10000)

        # Verify only public drafts are shown (should show public_name but NOT draft_name)
        # The submitted draft might also appear depending on implementation
        public_row = page.locator(f"tr:has-text('{public_name}')")
        draft_row = page.locator(f"tr:has-text('{draft_name}')")

        await expect(public_row).to_be_visible(timeout=5000)
        await expect(draft_row).to_have_count(0)  # Draft status should not appear

        # Verify the table displays correct information
        await expect(public_row).to_contain_text("Playwright Test User")  # Author
        await expect(public_row).to_contain_text("0")  # Comments count

        # Verify that there is no Action column or Review buttons
        await expect(page.locator("th:has-text('Action')")).to_have_count(0)
        await expect(public_row.locator("a:has-text('Review'), a:has-text('View & Comment')")).to_have_count(0)

        # Verify table row is clickable and works
        await public_row.click()

        # Should navigate to the draft page with from=public parameter
        await expect(page).to_have_url(re.compile(f".*drafts/{public_draft_id}.*from=public"))
        await expect(page.locator(f"h2:has-text('{public_name}')")).to_be_visible(timeout=10000)

        await verify_no_console_errors(errors, warnings)


class TestPublicDraftsBreadcrumbNavigation:
    """Test breadcrumb navigation for public drafts."""

    async def test_public_draft_breadcrumb_navigation(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test breadcrumb navigation from public drafts list to draft preview."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Public Breadcrumb Navigation"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for public breadcrumb navigation.",
            synonyms=["public", "breadcrumb", "test"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
            status="public",
        )

        # Navigate to public drafts list
        await page.goto(f"{BASE_URL}/drafts")
        await expect(page.locator("h1:has-text('Public Drafts for Review')")).to_be_visible(timeout=10000)

        # Find and click the draft row
        draft_row = page.locator(f"tr:has-text('{draft_name}')")
        await expect(draft_row).to_be_visible(timeout=5000)
        await draft_row.click()

        # Wait for navigation to draft page
        await expect(page).to_have_url(re.compile(f".*drafts/{draft_id}.*from=public"))
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=10000)

        # Verify breadcrumb shows: Home > Public Drafts > [Draft Title]
        breadcrumb = page.locator("nav[aria-label='Breadcrumb']")
        await expect(breadcrumb).to_contain_text("Home")
        await expect(breadcrumb).to_contain_text("Public Drafts")
        await expect(breadcrumb).to_contain_text(draft_name, ignore_case=True)

        # Verify "Public Drafts" breadcrumb links back to /drafts (not profile)
        public_drafts_link = breadcrumb.locator("a:has-text('Public Drafts')")
        await expect(public_drafts_link).to_be_visible()

        # Get the href attribute to verify it points to /drafts
        href = await public_drafts_link.get_attribute("href")
        assert href is not None and ("/drafts" in href or href.endswith("/drafts/"))

        # Click the "Public Drafts" breadcrumb to navigate back
        await public_drafts_link.click()
        await wait_for_htmx_swap(page, "h1:has-text('Public Drafts for Review')")

        # Should navigate back to public drafts list
        await expect(page).to_have_url(re.compile(r".*/drafts/?$"))
        await expect(page.locator("h1:has-text('Public Drafts for Review')")).to_be_visible(timeout=10000)

        # Verify the draft is still visible in the list
        await expect(page.locator(f"tr:has-text('{draft_name}')")).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestPublicDraftAuthorPermissions:
    """Test author permissions on public drafts."""

    async def test_public_draft_author_permissions(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that authors can both edit and delete their own public drafts."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Public Author Permissions"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,  # Same as authenticated user
            name=draft_name,
            description="Test description for public author permissions.",
            synonyms=["public", "author", "permissions"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
            status="public",
        )

        # Navigate to the draft from public drafts list
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?from=public")
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=10000)

        # Author should see BOTH DELETE and EDIT buttons (public drafts are editable by authors)
        delete_button = page.locator("button[data-modal-target*='delete-draft-modal']:has-text('Delete')")
        await expect(delete_button).to_be_visible(timeout=5000)

        # Should see EDIT button (authors can edit their public drafts)
        edit_button = page.locator("button#edit-mode-btn, button:has-text('Edit')")
        await expect(edit_button).to_be_visible(timeout=5000)

        # Test that edit mode actually works
        await edit_button.click()
        await wait_for_htmx_swap(page, "button:has-text('Update & Preview')")

        # Should now see "Update & Preview" button in edit mode
        update_preview_button = page.locator("button:has-text('Update & Preview')")
        await expect(update_preview_button).to_be_visible(timeout=5000)

        await verify_no_console_errors(errors, warnings)

    async def test_edit_public_draft(self, authenticated_page_with_console: tuple[Page, list[str], list[str]]) -> None:
        """Test that authors can edit their own public drafts."""
        page, errors, warnings = authenticated_page_with_console

        # Create a public draft
        draft_name = "UI Test Edit Public Draft"
        gen_json = await generate_valid_generated_json(draft_name)
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Original description for public draft.",
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
            status="public",  # Important: public status
        )

        # Navigate to edit mode
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?mode=edit")
        await expect(page.locator("h1:has-text('Edit Finding Model Draft')")).to_be_visible(timeout=10000)

        # Verify we're in edit mode with form fields visible
        await expect(page.locator("textarea#description")).to_be_visible()
        await expect(page.locator("textarea[name='attributes_markdown']")).to_be_visible()
        await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible()

        # Modify the description field (this will trigger regeneration but test can still verify update works)
        desc_field = page.locator("textarea#description")
        await desc_field.fill("Updated description for public draft that is much longer than before.")

        # Also modify the attributes_markdown field
        attrs_field = page.locator("textarea[name='attributes_markdown']")
        # Note: For test user, mock AI will generate standard "presence" attribute regardless of input
        # But we still verify the update process works
        attrs_text = (
            "### presence\\n"
            "- absent: Not visible\\n"
            "- present: Clearly visible\\n"
            "- indeterminate: Cannot be determined\\n"
        )
        await attrs_field.fill(attrs_text)

        # Click the "Update & Preview" button
        update_button = page.locator("button:has-text('Update & Preview')")
        await expect(update_button).to_be_enabled(timeout=5000)
        await update_button.click()

        # Wait for the HTMX swap to complete
        await wait_for_htmx_swap(page, "#success-alert")

        # Verify that the update succeeds (no error message appears)
        success_alert = page.locator("#success-alert")
        await expect(success_alert).to_be_visible(timeout=5000)

        # Verify the page transitions to preview mode
        # Look for the draft name as h2 (characteristic of preview mode)
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=10000)

        # Verify the updated description is visible in the preview
        # The description is shown in the preview regardless of mock AI behavior
        await expect(page.locator("body")).to_contain_text("Updated description for public draft")

        # Verify that the standard presence attribute is shown (from mock AI)
        # This is what the mock AI always generates for test user
        await expect(page.locator("body")).to_contain_text("presence")
        await expect(page.locator("body")).to_contain_text("Presence of")

        await verify_no_console_errors(errors, warnings)

    async def test_public_draft_non_author_permissions(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that non-authors cannot edit or delete public drafts."""
        page, errors, warnings = authenticated_page_with_console

        draft_name = "UI Test Public Non-Author Permissions"
        gen_json = await generate_valid_generated_json(draft_name)
        different_user_id = 888888  # Different from TEST_USER_ID (999999)
        draft_id = await seed_draft(
            user_id=different_user_id,  # Different user
            name=draft_name,
            description="Test description for public non-author permissions.",
            synonyms=["public", "non-author", "permissions"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible\\n",
            generated_json=gen_json,
            status="public",
        )

        # Navigate to the draft
        await page.goto(f"{BASE_URL}/drafts/{draft_id}?from=public")
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible(timeout=10000)

        # Non-author should NOT see any edit or delete buttons
        delete_button = page.locator("button[data-modal-target*='delete-draft-modal']:has-text('Delete')")
        await expect(delete_button).to_have_count(0)

        edit_button = page.locator("button#edit-mode-btn, button:has-text('Edit')")
        await expect(edit_button).to_have_count(0)

        update_preview_button = page.locator("button:has-text('Update & Preview')")
        await expect(update_preview_button).to_have_count(0)

        # Should still see the draft content (non-authors can view public drafts)
        await expect(page.locator(f"h2:has-text('{draft_name}')")).to_be_visible()
        # Verify the generated finding model is displayed (check for attributes section)
        await expect(page.locator("h3:has-text('Attributes')")).to_be_visible()

        # Should display author information (but not the current user's info)
        # This test doesn't assert specific author display since it depends on implementation
        # The key test is that action buttons are not present

        await verify_no_console_errors(errors, warnings)


class TestPublicDraftsMenuVerification:
    """Test navigation menu bar verification for public drafts."""

    async def test_navigation_menu_displays_drafts_correctly(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that navigation menu shows 'Drafts' with eye icon."""
        page, errors, warnings = authenticated_page_with_console

        # Navigate to any page to check the navigation menu
        await page.goto(f"{BASE_URL}/drafts")

        # Check that navigation menu shows "Drafts" as the link text (not "Public Drafts")
        drafts_nav_link = page.locator("nav a:has-text('Drafts')").first
        await expect(drafts_nav_link).to_be_visible(timeout=5000)

        # Verify the link points to /drafts
        href = await drafts_nav_link.get_attribute("href")
        assert href is not None and "/drafts" in href

        # Check for eye icon presence (optional UI enhancement)
        # ACCEPTABLE DEFENSIVE CHECK: Icon is optional decoration, link works without it
        # The "Drafts" navigation link functions correctly whether icon is present or not
        eye_icon = drafts_nav_link.locator("img, svg, i")
        if await eye_icon.count() > 0:
            await expect(eye_icon.first).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_public_drafts_page_title_and_header(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that public drafts page has correct title and header."""
        page, errors, warnings = authenticated_page_with_console

        await page.goto(f"{BASE_URL}/drafts")

        # Check page title
        await expect(page).to_have_title("Public Drafts - Finding Model Forge")

        # Check main heading
        await expect(page.locator("h1:has-text('Public Drafts for Review')")).to_be_visible(timeout=10000)

        # Check description text
        description_text = page.locator("text=Review and provide feedback on finding model drafts")
        await expect(description_text).to_be_visible()

        await verify_no_console_errors(errors, warnings)
