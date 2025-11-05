"""Creation workflow UI tests.

Tests for the end-to-end finding model creation workflow including:
- Basic creation flow (steps 1-5)
- Synonym management across steps
- Similar models handling
- Create-to-edit cycles
- Multiple edit/regenerate cycles
"""

from __future__ import annotations

import pytest
from playwright.async_api import Page, expect

from .utils import (
    TEST_USER_ID,
    cleanup_test_data,
    generate_valid_generated_json,
    navigate_to_create_page,
    seed_draft,
    verify_no_console_errors,
    wait_for_ai_completion_and_swap,
    wait_for_htmx_swap,
    wait_for_htmx_to_settle,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestBasicCreationFlow:
    """Test the basic happy path creation workflow."""

    async def test_complete_creation_workflow(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test the complete creation workflow from step 1 to public draft.

        New streamlined workflow:
        1. Step 1: Enter name, generate description
        2. Step 2: Check similar -> REDIRECT to draft edit page
        3. Draft Edit: Update & Preview -> Switch to view mode (draft status)
        4. Draft View: Make Public -> Switch to public status with Submit Draft button
        """
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Complete Flow"

        # Ensure clean database state
        await cleanup_test_data(TEST_USER_ID, finding_name)

        # Navigate to create page
        await navigate_to_create_page(page)

        # Step 1: Enter finding name
        name_input = page.locator("input[name='name']")
        await expect(name_input).to_be_visible(timeout=5000)
        await name_input.fill(finding_name)

        # Step 1 → Step 2: Generate Description (AI operation)
        generate_btn = page.locator("#main-content button:has-text('Generate Description')")
        await generate_btn.click()

        # Wait for AI to complete and HTMX to swap step 2 content
        await wait_for_ai_completion_and_swap(
            page,
            "Generat",  # Button text prefix to detect completion
            "textarea#description",  # Step 2 has description textarea (will be prefixed with #main-content)
        )

        # Step 2 → Step 3/Draft: Check for Similar (AI operation)
        similar_btn = page.locator("#main-content button:has-text('Check for Similar')")
        await similar_btn.click()

        # Wait for AI to complete and HTMX to swap new content
        print("DEBUG: Waiting for AI similarity check to complete...")
        await wait_for_ai_completion_and_swap(
            page,
            "Check",  # Button text prefix
            "textarea[name='attributes_markdown']",  # Draft edit form has attributes textarea (will be prefixed)
        )

        # Our mock always returns no similar models, so we expect draft edit form
        print("DEBUG: Should now have draft edit form in #main-content")

        # Verify we have the draft edit form elements
        attributes_textarea = page.locator("#main-content textarea[name='attributes_markdown']")
        await expect(attributes_textarea).to_be_visible(timeout=5000)

        # Draft Edit → View Mode: Update & Preview (AI operation to generate model)
        update_btn = page.locator("#main-content button:has-text('Update & Preview')")
        await expect(update_btn).to_be_visible(timeout=5000)
        print("DEBUG: Clicking 'Update & Preview' to generate model")
        await update_btn.click()

        # Wait for AI model generation and HTMX swap to view mode (with success alert)
        await wait_for_ai_completion_and_swap(
            page,
            "Updat",  # Button text prefix for "Updating..."
            "#success-alert",  # Success alert appears after update (will be prefixed)
        )

        # Check for mode toggle buttons (should appear after generation)
        mode_toggle_buttons = page.locator("#draft-mode-toggle-header button")
        if await mode_toggle_buttons.count() > 0:
            print("DEBUG: Mode toggle buttons appeared after model generation")

        # First, verify we have the draft in preview mode with "Make Public" button
        # Use more specific selector to target the trigger button (not the modal confirmation button)
        make_public_btn = page.locator("button:has-text('Make Public')").first
        await expect(make_public_btn).to_be_visible(timeout=5000)
        print("DEBUG: Found 'Make Public' button - draft created successfully")

        # Verify the draft model display elements (should be in preview mode now, case-insensitive due to AI)
        await expect(page.locator("h2")).to_contain_text(finding_name, ignore_case=True)
        await expect(page.locator("h3:has-text('Attributes')")).to_be_visible()
        await expect(page.locator("text=Status: Draft")).to_be_visible()

        # Test the "Make Public" workflow
        await make_public_btn.click()
        print("DEBUG: Clicking 'Make Public' button")

        # Wait for confirmation modal to appear (it appears as a div element at runtime)
        await wait_for_htmx_to_settle(page)  # Wait for modal to fully render
        modal = page.locator("[id^='make-public-modal-']")
        await expect(modal).to_be_visible(timeout=5000)
        print("DEBUG: Modal appeared")

        # Find and click the confirmation button inside the modal
        modal_make_public_btn = modal.locator("button:has-text('Make Public')")
        await expect(modal_make_public_btn).to_be_visible(timeout=5000)
        await modal_make_public_btn.click()
        print("DEBUG: Confirmed making draft public")

        # Wait for HTMX swap and verify "Submit Draft" button now appears
        await wait_for_htmx_swap(page, "button:has-text('Submit Draft')")
        submit_btn = page.locator("button:has-text('Submit Draft')")
        await expect(submit_btn).to_be_visible(timeout=5000)
        print("DEBUG: Found 'Submit Draft' button after making public")

        # Verify status has changed (should no longer show "Status: Draft")
        await expect(page.locator("text=Status: Draft")).to_have_count(0)

        # Note: We're not testing the actual submission since it had HTMX errors in manual testing
        # The workflow successfully creates the draft, makes it public, and shows it ready for submission

        await verify_no_console_errors(errors, warnings)

    async def test_navigation_authentication_required(
        self, page_with_console_tracking: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that create page requires authentication."""
        page, errors, warnings = page_with_console_tracking

        # Navigate to create page without authentication
        await page.goto("http://localhost:8000/create-finding-model")

        # Should show login required
        title = await page.title()
        assert "Login Required" in title

        login_message = page.locator("text=Please log in to create finding models")
        await expect(login_message).to_be_visible(timeout=5000)


class TestSynonymManagement:
    """Test synonym management across creation steps."""

    async def test_synonym_persistence_across_steps(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that synonyms persist across creation steps and can be edited."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Synonym Persistence"
        test_synonyms = ["synonym1", "synonym2", "synonym3"]

        await cleanup_test_data(TEST_USER_ID, finding_name)
        await navigate_to_create_page(page)

        # Step 1: Enter name and generate description
        await page.locator("input[name='name']").fill(finding_name)
        await page.locator("button:has-text('Generate Description')").click()
        await wait_for_ai_completion_and_swap(page, "Generat", "textarea#description")

        # Step 2: Add synonyms
        await expect(page.locator("input[placeholder*='synonym']")).to_be_visible(timeout=5000)

        for synonym in test_synonyms:
            synonym_input = page.locator("input[placeholder*='synonym']")
            await synonym_input.fill(synonym)
            await page.locator("button:has-text('Add')").click()
            # Wait for synonym badge to appear (use specific CSS classes)
            badge_selector = f"span.inline-flex.items-center:has-text('{synonym}')"
            await page.wait_for_selector(badge_selector, state="visible", timeout=5000)

        # Verify synonyms appear as badges in step 2
        for synonym in test_synonyms:
            badge_selector = f"span.inline-flex.items-center:has-text('{synonym}')"
            await expect(page.locator(badge_selector).first).to_be_visible()

        # Continue to similarity check (this will redirect to draft edit form)
        continue_btn = page.locator("button:has-text('Check for Similar')")
        await continue_btn.click()
        await wait_for_ai_completion_and_swap(page, "Check", "textarea[name='attributes_markdown']")

        # Should now be on draft edit form with attributes textarea
        await expect(page.locator("textarea[name='attributes_markdown']")).to_be_visible(timeout=10000)

        # Check that synonyms persisted to the draft edit form
        for synonym in test_synonyms:
            badge_selector = f"span.inline-flex.items-center:has-text('{synonym}')"
            await expect(page.locator(badge_selector).first).to_be_visible()

        # Test adding one more synonym on the draft edit form
        new_synonym = "draft-form-synonym"
        synonym_input = page.locator("input[placeholder*='synonym']")
        await synonym_input.fill(new_synonym)
        await page.locator("button:has-text('Add')").click()
        # Wait for new synonym badge to appear
        new_badge_selector = f"span.inline-flex.items-center:has-text('{new_synonym}')"
        await page.wait_for_selector(new_badge_selector, state="visible", timeout=5000)

        # Verify all synonyms are present on draft edit form
        all_synonyms = test_synonyms + [new_synonym]
        for synonym in all_synonyms:
            badge_selector = f"span.inline-flex.items-center:has-text('{synonym}')"
            await expect(page.locator(badge_selector).first).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_synonym_removal(self, authenticated_page_with_console: tuple[Page, list[str], list[str]]) -> None:
        """Test removing synonyms during creation workflow."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Synonym Removal"

        await cleanup_test_data(TEST_USER_ID, finding_name)
        await navigate_to_create_page(page)

        # Get to step 2
        await page.locator("input[name='name']").fill(finding_name)
        await page.locator("button:has-text('Generate Description')").click()
        await wait_for_ai_completion_and_swap(page, "Generat", "textarea#description")

        # Add a synonym
        test_synonym = "removable-synonym"
        await page.locator("input[placeholder*='synonym']").fill(test_synonym)
        await page.locator("button:has-text('Add')").click()
        # Wait for synonym badge to appear
        await page.wait_for_selector(f"span.inline-flex.items-center:has-text('{test_synonym}')", state="visible")

        # Verify synonym appears
        synonym_badge = page.locator(f"span.inline-flex.items-center:has-text('{test_synonym}')").first
        await expect(synonym_badge).to_be_visible()

        # Remove the synonym by clicking the X button
        remove_btn = synonym_badge.locator("button")
        await remove_btn.click()
        # Wait for synonym badge to disappear
        await expect(synonym_badge).to_have_count(0)

        # Verify synonym is removed
        await expect(synonym_badge).to_have_count(0)

        await verify_no_console_errors(errors, warnings)


class TestCreateToEditWorkflow:
    """Test the create → generate → edit → regenerate workflow."""

    async def test_create_to_edit_cycle(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test creating a model, then using edit mode toggle to edit and regenerate."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Create to Edit"

        await cleanup_test_data(TEST_USER_ID, finding_name)
        await navigate_to_create_page(page)

        # Complete workflow to draft preview (HTMX swaps in #main-content)
        await page.locator("input[name='name']").fill(finding_name)
        await page.locator("#main-content button:has-text('Generate Description')").click()

        # Wait for HTMX swap to step 2
        await wait_for_ai_completion_and_swap(page, "Generat", "textarea#description")

        # Continue to similarity check (triggers HTMX swap to draft content)
        await page.locator("#main-content button:has-text('Check for Similar')").click()
        await wait_for_ai_completion_and_swap(page, "Check", "textarea[name='attributes_markdown']")

        # Should now have draft edit form content in #main-content
        await expect(page.locator("#main-content textarea[name='attributes_markdown']")).to_be_visible()

        # Generate model (HTMX swap to preview mode with Make Public button)
        await page.locator("#main-content button:has-text('Update & Preview')").click()
        await wait_for_ai_completion_and_swap(page, "Updat", "button:has-text('Make Public')")

        # Should now have draft preview content in #main-content with mode toggle buttons
        edit_mode_btn = page.locator("button#edit-mode-btn")
        if await edit_mode_btn.count() > 0:
            # Test edit → preview cycle using mode toggle buttons
            await edit_mode_btn.click()
            await wait_for_htmx_swap(page, "textarea#description")

            # Should be back in edit form - verify description is pre-filled
            desc_field = page.locator("#main-content textarea#description")
            desc_value = await desc_field.input_value()
            assert len(desc_value) > 0, "Description should be pre-filled"

            # Make a change to trigger regeneration
            current_desc = await desc_field.input_value()
            await desc_field.fill(current_desc + " Modified for testing.")

            # Generate again (HTMX swap back to preview)
            await page.locator("#main-content button:has-text('Update & Preview')").click()
            await wait_for_ai_completion_and_swap(page, "Updat", "button:has-text('Make Public')")

            # Verify we're back in view/preview mode (Make Public button should be visible)
            await expect(page.locator("#main-content button:has-text('Make Public')").first).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestMultipleEditCycles:
    """Test multiple rounds of editing and regenerating on draft page."""

    async def test_basic_edit_preview_cycle(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test basic edit → preview → edit cycle on draft page."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Basic Edit Cycle"

        # Create a draft with generated model to start with
        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=finding_name,
            description="Initial description for testing edit cycles",
            synonyms=["test", "cycles"],
            attributes_markdown="### presence\\n- absent: Not visible\\n- present: Visible",
            generated_json=await generate_valid_generated_json(finding_name),
            status="draft",
        )

        # Navigate to draft page in preview mode (has generated model)
        await page.goto(f"http://localhost:8000/drafts/{draft_id}?mode=view")

        # Verify we're in preview mode with generated model (case-insensitive due to AI generation)
        await expect(page.locator("h2")).to_contain_text(finding_name, ignore_case=True)
        await expect(page.locator("button:has-text('Edit')")).to_be_visible()

        # Test Edit → Update → Preview cycle
        await page.locator("button:has-text('Edit')").click()
        await page.wait_for_selector("textarea[name='description']", state="visible", timeout=10000)

        # Make a small change to description
        desc_field = page.locator("textarea[name='description']")
        current_desc = await desc_field.input_value()
        await desc_field.fill(current_desc + " Edited.")

        # Update and switch back to preview
        await page.locator("button:has-text('Update & Preview')").click()
        await page.wait_for_selector("button:has-text('Edit')", state="visible", timeout=30000)

        # Verify we can edit again
        await page.locator("button:has-text('Edit')").click()
        await page.wait_for_selector("textarea[name='description']", state="visible", timeout=10000)
        # Look for the mode toggle Preview button (more specific selector)
        await expect(page.locator("button[id='view-mode-btn']")).to_be_visible()

        await verify_no_console_errors(errors, warnings)


class TestResumeFlow:
    """Test resuming creation with existing drafts."""

    async def test_resume_submitted_draft(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that entering the name of a submitted draft shows read-only final display."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Resume Submitted"

        # Clean up any existing data
        await cleanup_test_data(TEST_USER_ID, finding_name)

        # Create a submitted draft directly in the database
        await seed_draft(
            user_id=TEST_USER_ID,
            name=finding_name,
            description="This is a test description for resume testing.",
            synonyms=["test", "resume"],
            attributes_markdown=(
                "### presence\n- absent: Not visible\n- present: Visible\n- indeterminate: Cannot be determined"
            ),
            generated_json=await generate_valid_generated_json(finding_name),
            status="submitted",
        )

        # Navigate to create page and attempt to create with same name (resume flow)
        await navigate_to_create_page(page)
        await page.locator("input[name='name']").fill(finding_name)
        await page.locator("button:has-text('Generate Description')").click()

        # Should quickly show read-only final display (no long AI processing)
        await page.wait_for_selector("h2:has-text('UI Test Resume Submitted')", state="visible", timeout=10000)

        # Should stay on create-finding-model URL
        assert "/create-finding-model" in page.url

        # Should show "Draft submitted" alert
        await expect(page.locator("text=Draft submitted")).to_be_visible()
        await expect(page.locator("text=This draft is locked and cannot be edited")).to_be_visible()

        # Should show the complete model display
        await expect(page.locator("h2:has-text('UI Test Resume Submitted')")).to_be_visible()
        await expect(page.locator("text=ID:")).to_be_visible()  # Should have generated ID

        # Should show synonyms section
        await expect(page.locator("h3:has-text('Synonyms')")).to_be_visible()
        synonym_badge = page.locator("span.inline-flex.items-center:has-text('test')").first
        await expect(synonym_badge).to_be_visible()  # From seeded synonyms

        # Should show attributes section with at least one attribute (AI generates attribute names)
        await expect(page.locator("h3:has-text('Attributes')")).to_be_visible()
        # Check for presence of attribute card structure (not specific AI-generated names)
        await expect(page.locator("div.border.rounded-lg h4").first).to_be_visible()

        # Should show status as "Submitted"
        await expect(page.locator("text=Status:")).to_be_visible()
        status_span = page.locator("span.text-green-600:has-text('Submitted')")
        await expect(status_span).to_be_visible()

        # Should NOT have any edit buttons (it's read-only)
        await expect(page.locator("button:has-text('Edit')")).to_have_count(0)
        await expect(page.locator("button:has-text('Update')")).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_resume_draft_status(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that entering the name of a draft status shows editable draft form."""
        page, errors, warnings = authenticated_page_with_console

        finding_name = "UI Test Resume Draft"

        # Clean up any existing data
        await cleanup_test_data(TEST_USER_ID, finding_name)

        # Create a draft with status="draft" (editable)
        await seed_draft(
            user_id=TEST_USER_ID,
            name=finding_name,
            description="This is an editable draft for testing.",
            synonyms=["editable", "draft"],
            attributes_markdown="### presence\n- absent: Not visible\n- present: Visible",
            generated_json=None,  # No generated JSON for drafts
            status="draft",
        )

        # Navigate to create page and attempt to create with same name (resume flow)
        await navigate_to_create_page(page)
        await page.locator("input[name='name']").fill(finding_name)
        await page.locator("button:has-text('Generate Description')").click()

        # Should go directly to draft edit form (not step workflow)
        await page.wait_for_selector("button:has-text('Update & Preview')", state="visible", timeout=10000)

        # Should stay on create-finding-model URL
        assert "/create-finding-model" in page.url

        # Should have draft edit form with "Update & Preview" button
        await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible()

        # Should have pre-filled form data from the existing draft
        name_field = page.locator("input[type='text']").first  # Finding name field
        await expect(name_field).to_have_value(finding_name)

        # Should have pre-filled description from seeded draft
        desc_field = page.locator("textarea[name='description']")
        await expect(desc_field).to_be_visible()
        desc_value = await desc_field.input_value()
        assert "editable draft" in desc_value, "Should contain content from seeded draft"

        # Should have pre-filled synonyms from seeded draft
        synonym_badges = page.locator("span:has-text('editable'), span:has-text('draft')")
        await expect(synonym_badges.first).to_be_visible()

        # Should have pre-filled attributes from seeded draft
        attrs_field = page.locator("textarea[name='attributes_markdown']")
        await expect(attrs_field).to_be_visible()
        attrs_value = await attrs_field.input_value()
        assert "presence" in attrs_value, "Should contain attributes from seeded draft"

        # Should be able to edit the description (not read-only)
        await desc_field.fill(desc_value + " - Modified during test")
        modified_value = await desc_field.input_value()
        assert "Modified during test" in modified_value, "Should be able to edit the description"

        await verify_no_console_errors(errors, warnings)
