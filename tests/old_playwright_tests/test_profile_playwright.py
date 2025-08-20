"""Playwright UI tests for the Profile page drafts grid and actions.

These tests validate that:
- Draft and submitted cards render with appropriate actions
- View/Edit/Delete buttons behave as expected
- Delete modal only exists for drafts and deletion removes the card
- No Flowbite modal console errors occur during interactions
"""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from typing import Any

import pytest
from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from playwright.async_api import ConsoleMessage, Page, async_playwright, expect

from app.config import settings

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


async def _generate_valid_generated_json(name: str) -> str:
    """Create a valid FindingModel JSON string for a submitted draft using the findingmodel library.

    We keep it minimal but valid to ensure the draft view page shows JSON accordion.
    """
    from findingmodel import FindingInfo
    from findingmodel.tools import (
        add_ids_to_model,
        add_standard_codes_to_model,
        create_model_from_markdown,
    )

    description = f"A test finding model for {name}."  # >= 10 chars
    attributes_md = f"""
### presence

Presence of {name}

- absent: Not visible
- present: Visible
- indeterminate: Cannot be determined
"""

    md = f"# {name}\n\n## Description\n{description}\n\n{attributes_md}\n"
    info = FindingInfo(name=name, description=description, synonyms=["test"])  # type: ignore[call-arg]

    fm = await create_model_from_markdown(info, markdown_text=md)
    # Add IDs and standard codes to satisfy display logic
    fm = add_ids_to_model(fm, source="OIDM")
    add_standard_codes_to_model(fm)
    return fm.model_dump_json(exclude_none=True)


async def _seed_drafts(
    *,
    user_id: int,
    draft_name: str,
    submitted_name: str,
) -> dict[str, str]:
    """Insert one draft and one submitted document for the test user.

    Returns a dict with the inserted IDs: {"draft_id": str, "submitted_id": str}
    """
    client: Any = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db["finding_model_drafts"]

    # Cleanup ALL previous test docs for stability for this user
    await col.delete_many({"user_id": user_id})

    now = datetime.now(UTC)

    draft_oid = ObjectId()
    submitted_oid = ObjectId()

    draft_doc = {
        "_id": draft_oid,
        "user_id": user_id,
        "name": draft_name,
        "created_at": now,
        "updated_at": now,
        "inputs": {
            "description": f"Draft description for {draft_name}.",
            "synonyms": ["alpha"],
            "attributes_markdown": "### presence\n- absent: a\n- present: b\n- indeterminate: c\n",
        },
        "generated_json": None,
        "status": "draft",
        "action_log": [],
    }

    gen_json = await _generate_valid_generated_json(submitted_name)
    submitted_doc = {
        "_id": submitted_oid,
        "user_id": user_id,
        "name": submitted_name,
        "created_at": now,
        "updated_at": now,
        "inputs": {
            "description": f"Submitted description for {submitted_name}.",
            "synonyms": ["beta"],
            "attributes_markdown": "### presence\n- absent: a\n- present: b\n- indeterminate: c\n",
        },
        "generated_json": gen_json,
        "status": "submitted",
        "action_log": [],
    }

    await col.insert_many([draft_doc, submitted_doc])
    # Ensure writes are committed
    await db.command("ping")
    client.close()
    return {"draft_id": str(draft_oid), "submitted_id": str(submitted_oid)}


def _collect_console(page: Page) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        text = msg.text or ""
        if msg.type == "error":
            errors.append(text)
        elif msg.type == "warning":
            warnings.append(text)

    page.on("console", on_console)  # type: ignore[arg-type]

    def on_page_error(err: Exception) -> None:  # noqa: ANN001 - third-party signature shape
        errors.append(str(err))

    page.on("pageerror", on_page_error)  # type: ignore[arg-type]
    return errors, warnings


class TestProfileDraftsUI:
    async def test_profile_drafts_actions_and_modals(self) -> None:
        """End-to-end validation of drafts grid actions and modal behavior on Profile page."""
        test_user_id = int(os.getenv("TEST_AUTH_USER_ID", "999999"))
        draft_name = "PW Draft One"
        submitted_name = "PW Submitted One"

        ids = await _seed_drafts(user_id=test_user_id, draft_name=draft_name, submitted_name=submitted_name)
        draft_id = ids["draft_id"]
        submitted_id = ids["submitted_id"]

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()
            errors, warnings = _collect_console(page)

            try:
                # Authenticate via test route
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")

                # Navigate to Profile
                await page.goto("http://localhost:8000/profile")
                # Wait specifically for the drafts grid to be visible (we just seeded drafts)
                await expect(page.locator("#drafts-grid")).to_be_visible(timeout=10000)

                grid = page.locator("#drafts-grid")
                if await grid.count() == 0:
                    pytest.fail("Drafts grid not found on profile page")

                # Cards should include one draft and one submitted
                draft_card = grid.locator(f".draft-card:has-text('{draft_name}')")
                submitted_card = grid.locator(f".draft-card:has-text('{submitted_name}')")
                await expect(draft_card).to_be_visible()
                await expect(submitted_card).to_be_visible()

                # Submitted card should NOT have Delete or Edit, and no delete modal in DOM
                await expect(submitted_card.locator("a[title='Delete'], button[title='Delete']")).to_have_count(0)
                await expect(submitted_card.locator("a[title='Edit'], button[title='Edit']")).to_have_count(0)
                await expect(page.locator(f"#delete-draft-modal-{submitted_id}")).to_have_count(0)

                # Draft card should have Edit/Delete (View only appears if has_generated)
                await expect(draft_card.locator("a[title='Edit'], button[title='Edit']")).to_have_count(1)
                await expect(draft_card.locator("a[title='Delete'], button[title='Delete']")).to_have_count(1)
                # View button may or may not be present for drafts depending on whether they have generated JSON

                # 1) View draft: only test if View button is present (depends on has_generated)
                view_button_count = await draft_card.locator("a[title='View'], button[title='View']").count()
                if view_button_count > 0:
                    await draft_card.locator("a[title='View'], button[title='View']").first.click()
                    await page.wait_for_load_state("networkidle")
                    # JSON accordion must be absent for drafts without submitted status
                    await expect(page.locator("#finding-model-json")).to_have_count(0)
                    # Return back
                    await page.go_back()
                    await page.wait_for_selector("#drafts-grid")

                # 2) View submitted: JSON accordion should be present
                await submitted_card.locator("a[title='View'], button[title='View']").first.click()
                await page.wait_for_load_state("networkidle")
                await expect(page.locator("#finding-model-json")).to_have_count(1)
                # Go back to profile
                await page.go_back()
                await page.wait_for_selector("#drafts-grid")

                # 3) Edit draft: should navigate to unified draft page in edit mode
                await draft_card.locator("a[title='Edit'], button[title='Edit']").first.click()
                await page.wait_for_load_state("networkidle")
                # Expect unified draft edit page elements
                await expect(page.locator("h1:has-text('Edit Finding Model Draft')")).to_be_visible(timeout=10000)
                await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible(timeout=10000)
                # Should have description and attributes textareas
                await expect(page.locator("textarea#description")).to_be_visible()
                await expect(page.locator("textarea[name='attributes_markdown']")).to_be_visible()
                await page.go_back()
                await page.wait_for_selector("#drafts-grid")

                # 4) Delete draft: open modal and confirm deletion
                await draft_card.locator("a[title='Delete'], button[title='Delete']").first.click()
                modal = page.locator(f"#delete-draft-modal-{draft_id}")
                await expect(modal).to_be_visible(timeout=5000)
                await modal.locator("button:has-text('Yes, delete')").click()
                # After HTMX swap, the card should be removed
                await expect(page.locator(f"#draft-card-{draft_id}")).to_have_count(0)
                # No-drafts placeholder should remain hidden because submitted still exists
                await expect(page.locator("#no-drafts")).to_have_class(re.compile(r".*\bhidden\b.*"))

                # Ensure no Flowbite or Alpine console errors
                bad_keywords = [
                    "Flowbite",
                    "Modal",
                    "not been initialized",
                    "does not exist",
                    "Alpine Expression Error",
                    "SyntaxError",
                    "Unexpected keyword",
                ]
                offending = [e for e in errors if any(k.lower() in e.lower() for k in bad_keywords)]
                assert not offending, f"Console errors found: {offending}"

            finally:
                await browser.close()


class TestProfileNoDraftsState:
    async def test_delete_last_draft_shows_placeholder(self) -> None:
        """When the last draft is deleted, the 'no drafts' message should appear and grid hides."""
        test_user_id = int(os.getenv("TEST_AUTH_USER_ID", "999999"))
        only_draft_name = "PW Single Draft"

        # Seed a single draft and no submitted
        client: Any = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db["finding_model_drafts"]
        # Ensure a clean slate for this user (remove any lingering drafts/submitted)
        await col.delete_many({"user_id": test_user_id})
        now = datetime.now(UTC)
        draft_oid = ObjectId()
        await col.insert_one(
            {
                "_id": draft_oid,
                "user_id": test_user_id,
                "name": only_draft_name,
                "created_at": now,
                "updated_at": now,
                "inputs": {
                    "description": f"Draft description for {only_draft_name}.",
                    "synonyms": ["gamma"],
                    "attributes_markdown": "### presence\n- absent: a\n- present: b\n- indeterminate: c\n",
                },
                "generated_json": None,
                "status": "draft",
                "action_log": [],
            }
        )
        await db.command("ping")
        client.close()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()
            errors, warnings = _collect_console(page)

            try:
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")
                await page.goto("http://localhost:8000/profile")
                await page.wait_for_selector("#drafts-grid")

                card = page.locator(f"#drafts-grid .draft-card:has-text('{only_draft_name}')")
                await expect(card).to_be_visible()
                await card.locator("a[title='Delete'], button[title='Delete']").first.click()
                modal = page.locator(f"#delete-draft-modal-{draft_oid}")
                await expect(modal).to_be_visible(timeout=5000)
                await modal.locator("button:has-text('Yes, delete')").click()

                # Card should be removed, and placeholder should show
                await expect(page.locator(f"#draft-card-{draft_oid}")).to_have_count(0)
                await expect(page.locator("#no-drafts")).to_be_visible()

                # Ensure no Flowbite or Alpine console errors
                bad_keywords = [
                    "Flowbite",
                    "Modal",
                    "not been initialized",
                    "does not exist",
                    "Alpine Expression Error",
                    "SyntaxError",
                    "Unexpected keyword",
                ]
                offending = [e for e in errors if any(k.lower() in e.lower() for k in bad_keywords)]
                assert not offending, f"Console errors found: {offending}"

            finally:
                await browser.close()


class TestFormValidation:
    async def test_button_validation_for_draft_with_generated_model(self) -> None:
        """Test that Update & Preview button validation works correctly for drafts with existing models."""
        test_user_id = int(os.getenv("TEST_AUTH_USER_ID", "999999"))
        draft_name = "PW Validation Draft"

        # Seed a single draft with generated_json (existing model)
        client: Any = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db["finding_model_drafts"]
        await col.delete_many({"user_id": test_user_id})
        now = datetime.now(UTC)
        draft_oid = ObjectId()
        gen_json = await _generate_valid_generated_json(draft_name)
        await col.insert_one(
            {
                "_id": draft_oid,
                "user_id": test_user_id,
                "name": draft_name,
                "created_at": now,
                "updated_at": now,
                "inputs": {
                    "description": f"Draft description for {draft_name}.",
                    "synonyms": ["alpha"],
                    "attributes_markdown": "### presence\n- absent: a\n- present: b\n- indeterminate: c\n",
                },
                "generated_json": gen_json,
                "status": "draft",
                "action_log": [],
            }
        )
        await db.command("ping")
        client.close()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            context = await browser.new_context()
            page = await context.new_page()

            try:
                # Authenticate
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")
                # Go to profile
                await page.goto("http://localhost:8000/profile")
                await page.wait_for_selector("#drafts-grid")
                # Click Edit on the seeded draft
                card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
                await expect(card).to_be_visible()
                await card.locator("a[title='Edit'], button[title='Edit']").first.click()
                await page.wait_for_load_state("networkidle")
                await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible()

                # Wait for Alpine.js to initialize and form to be populated
                await page.wait_for_timeout(3000)

                button = page.locator("button:has-text('Update & Preview')")

                # Test 1: Button should be DISABLED initially (no changes + has existing model)
                await expect(button).to_be_disabled(timeout=5000)

                # Test 2: Make a change - button should become ENABLED
                desc_field = page.locator("textarea#description")
                current_desc = await desc_field.input_value()
                await desc_field.fill(current_desc + " Updated content.")
                await page.wait_for_timeout(500)  # Wait for Alpine reactivity

                await expect(button).to_be_enabled(timeout=5000)

                # Test 3: Revert the change - button should become DISABLED again
                await desc_field.fill(current_desc)
                await page.wait_for_timeout(500)  # Wait for Alpine reactivity

                await expect(button).to_be_disabled(timeout=5000)

                # Test 4: Change attributes instead - button should become ENABLED
                attrs_field = page.locator("textarea[name='attributes_markdown']")
                current_attrs = await attrs_field.input_value()
                await attrs_field.fill(current_attrs + "\n- new: attribute")
                await page.wait_for_timeout(500)

                await expect(button).to_be_enabled(timeout=5000)

                # Test 5: Can successfully submit with changes
                await button.click()

                # Wait for HTMX to complete the content swap
                await page.wait_for_timeout(2000)

                # Should see success message
                success_alert = page.locator("#success-alert")
                await expect(success_alert).to_be_visible(timeout=5000)
                await expect(success_alert).to_contain_text("Draft updated successfully!")

            finally:
                await browser.close()


class TestBackFromReviewKeepsForm:
    async def test_back_from_step5_prefills_step4(self) -> None:
        """After generating (step 5), clicking Back returns to step 4 with prefilled values."""
        test_user_id = int(os.getenv("TEST_AUTH_USER_ID", "999999"))
        draft_name = "PW Back Prefill"

        # Seed a single draft with generated_json and known inputs
        client: Any = AsyncIOMotorClient(settings.mongodb_uri)
        db = client[settings.mongodb_db]
        col = db["finding_model_drafts"]
        await col.delete_many({"user_id": test_user_id})
        now = datetime.now(UTC)
        draft_oid = ObjectId()
        seeded_description = f"Draft description for {draft_name}."
        seeded_synonyms = ["alpha", "omega"]
        seeded_attrs = "### presence\n- absent: a\n- present: b\n- indeterminate: c\n"
        gen_json = await _generate_valid_generated_json(draft_name)
        await col.insert_one(
            {
                "_id": draft_oid,
                "user_id": test_user_id,
                "name": draft_name,
                "created_at": now,
                "updated_at": now,
                "inputs": {
                    "description": seeded_description,
                    "synonyms": seeded_synonyms,
                    "attributes_markdown": seeded_attrs,
                },
                "generated_json": gen_json,
                "status": "draft",
                "action_log": [],
            }
        )
        await db.command("ping")
        client.close()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Authenticate and go to profile
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")
                await page.goto("http://localhost:8000/profile")
                await page.wait_for_selector("#drafts-grid")

                # Edit the seeded draft - lands on unified draft edit page
                card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
                await expect(card).to_be_visible()
                await card.locator("a[title='Edit'], button[title='Edit']").first.click()
                await page.wait_for_load_state("networkidle")
                await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible()

                # Wait for form to load and ensure button is enabled
                await page.wait_for_timeout(2000)
                button = page.locator("button:has-text('Update & Preview')")
                is_enabled = await button.is_enabled()
                if not is_enabled:
                    # Make a minimal change to enable the button
                    desc_field = page.locator("textarea#description")
                    current_desc = await desc_field.input_value()
                    await desc_field.fill(current_desc + " (test update)")
                    await page.wait_for_timeout(500)

                # Click Update & Preview - this will trigger HTMX content swap
                await page.locator("button:has-text('Update & Preview')").click()

                # Wait for HTMX to complete the content swap
                await page.wait_for_timeout(2000)

                # Look for the success alert that appears after update
                success_alert = page.locator("#success-alert")
                await expect(success_alert).to_be_visible(timeout=5000)
                await expect(success_alert).to_contain_text("Draft updated successfully!")

                # For drafts, we should be able to switch back to edit mode using the Edit button
                edit_mode_btn = page.locator("button#edit-mode-btn")
                await expect(edit_mode_btn).to_be_visible()
                await edit_mode_btn.click()

                # Should be back on edit mode of unified draft page with prefilled values
                await expect(page.locator("button:has-text('Update & Preview')")).to_be_visible(timeout=10000)

                # Description textarea should contain seeded text
                desc = page.locator("textarea#description")
                await expect(desc).to_be_visible()
                desc_val = await desc.input_value()
                assert seeded_description in desc_val, f"Description not prefilled. Got: {desc_val!r}"

                # Attributes textarea should contain seeded attributes
                attrs = page.locator("textarea#attributes_markdown")
                await expect(attrs).to_be_visible()
                attrs_val = await attrs.input_value()
                assert "### presence" in attrs_val and "- absent:" in attrs_val, "Attributes not prefilled"

                # Synonyms badges should include both seeded synonyms (scope to badge container to avoid duplicates)
                badges = page.locator("div.flex.flex-wrap.gap-2.mb-3 >> span.inline-flex.items-center")
                for syn in seeded_synonyms:
                    await expect(badges.filter(has_text=syn)).to_be_visible()

            finally:
                await browser.close()
