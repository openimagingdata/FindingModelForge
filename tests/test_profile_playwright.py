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

                # Draft card should have View/Edit/Delete
                await expect(draft_card.locator("a[title='View'], button[title='View']")).to_have_count(1)
                await expect(draft_card.locator("a[title='Edit'], button[title='Edit']")).to_have_count(1)
                await expect(draft_card.locator("a[title='Delete'], button[title='Delete']")).to_have_count(1)

                # 1) View draft: should NOT show JSON or IDs
                await draft_card.locator("a[title='View'], button[title='View']").first.click()
                await page.wait_for_load_state("networkidle")
                # JSON accordion must be absent for drafts
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

                # 3) Edit draft: should navigate to create page with draft loaded (step 4 UI present)
                await draft_card.locator("a[title='Edit'], button[title='Edit']").first.click()
                await page.wait_for_load_state("networkidle")
                # Expect Edit Attributes step elements (Show Model button)
                await expect(page.locator("button:has-text('Show Model')")).to_be_visible(timeout=10000)
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


class TestReuseOnShowModel:
    async def test_reuse_generated_json_when_inputs_unchanged(self) -> None:
        """Editing a draft and clicking Show Model should reuse generated_json if inputs are unchanged."""
        test_user_id = int(os.getenv("TEST_AUTH_USER_ID", "999999"))
        draft_name = "PW Reuse Draft"

        # Seed a single draft with generated_json
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
                await expect(page.locator("button:has-text('Show Model')")).to_be_visible()

                # Intercept the POST to step/4 and capture the response headers
                reuse_flag: dict[str, str] = {}

                def on_response(response: Any) -> None:  # Playwright Response
                    try:
                        if "/api/finding-models/create/step/4" in response.url and response.request.method == "POST":
                            val = response.headers.get("x-model-reused")
                            if val is not None:
                                reuse_flag["x-model-reused"] = val
                    except Exception:
                        pass

                page.on("response", on_response)  # type: ignore[arg-type]

                # Click Show Model without changing inputs
                await page.locator("button:has-text('Show Model')").click()
                # After swap, step 5 heading should be present (implicit wait for POST completion)
                await expect(page.locator("h2:has-text('Your Finding Model is Ready!')")).to_be_visible(timeout=20000)

                # Assert header indicates reuse
                assert reuse_flag.get("x-model-reused") == "1", f"Expected reuse header '1', got {reuse_flag}"

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

                # Edit the seeded draft to land on step 4
                card = page.locator(f"#drafts-grid .draft-card:has-text('{draft_name}')")
                await expect(card).to_be_visible()
                await card.locator("a[title='Edit'], button[title='Edit']").first.click()
                await page.wait_for_load_state("networkidle")
                await expect(page.locator("button:has-text('Show Model')")).to_be_visible()

                # Click Show Model to navigate to step 5
                await page.locator("button:has-text('Show Model')").click()
                await expect(page.locator("h2:has-text('Your Finding Model is Ready!')")).to_be_visible(timeout=20000)

                # Click Back to return to step 4
                back_btn = page.locator("button:has-text('Back')")
                await expect(back_btn).to_be_visible()
                await back_btn.click()

                # Step 4 should render with prefilled values
                await expect(page.locator("button:has-text('Show Model')")).to_be_visible(timeout=10000)

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
