"""Shared utilities for UI/Playwright tests."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from playwright.async_api import ConsoleMessage, Page

from app.config import settings

# Test user ID for authentication (hardcoded for test-auth system)
TEST_USER_ID = 999999  # This is hardcoded in the test-auth system


async def authenticate_user(page: Page) -> None:
    """Authenticate user via test-auth endpoint.

    This uses the test-auth system to log in user ID 999999
    and redirects to the create-finding-model page.
    """
    await page.goto("http://localhost:8000/test-auth/login")
    await page.wait_for_load_state("networkidle")


async def generate_valid_generated_json(name: str) -> str:
    """Create a valid FindingModel JSON string using the findingmodel library.

    Args:
        name: The finding model name

    Returns:
        Valid JSON string for a FindingModel
    """
    from findingmodel import FindingInfo
    from findingmodel.tools import (
        add_ids_to_model,
        add_standard_codes_to_model,
        create_model_from_markdown,
    )

    description = f"A test finding model for {name}."
    attributes_md = f"""
### presence

Presence of {name}

- absent: Not visible
- present: Visible
- indeterminate: Cannot be determined
"""

    md = f"# {name}\\n\\n## Description\\n{description}\\n\\n{attributes_md}\\n"
    info = FindingInfo(name=name, description=description, synonyms=["test"])  # type: ignore[call-arg]

    fm = await create_model_from_markdown(info, markdown_text=md)
    # Add IDs and standard codes to satisfy display logic
    fm = add_ids_to_model(fm, source="OIDM")
    add_standard_codes_to_model(fm)
    return fm.model_dump_json(exclude_none=True)


async def seed_draft(
    *,
    user_id: int,
    name: str,
    description: str | None = None,
    synonyms: list[str] | None = None,
    attributes_markdown: str | None = None,
    generated_json: str | None = None,
    status: str = "draft",
) -> str:
    """Create a test draft in the database.

    Args:
        user_id: User ID to associate with the draft
        name: Draft name
        description: Draft description (optional)
        synonyms: List of synonyms (optional)
        attributes_markdown: Attributes markdown content (optional)
        generated_json: Generated JSON content (optional)
        status: Draft status ('draft' or 'submitted')

    Returns:
        Draft ID as string
    """
    client: Any = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db["finding_model_drafts"]

    now = datetime.now(UTC)
    draft_oid = ObjectId()

    # Default values
    description = description or f"Test description for {name}."
    synonyms = synonyms or ["test"]
    attributes_markdown = attributes_markdown or "### presence\\n- absent: a\\n- present: b\\n- indeterminate: c\\n"

    draft_doc = {
        "_id": draft_oid,
        "user_id": user_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
        "inputs": {
            "description": description,
            "synonyms": synonyms,
            "attributes_markdown": attributes_markdown,
        },
        "generated_json": generated_json,
        "status": status,
        "action_log": [],
    }

    await col.insert_one(draft_doc)
    await db.command("ping")  # Ensure write is committed
    client.close()

    return str(draft_oid)


async def seed_drafts(
    *,
    user_id: int,
    draft_name: str,
    submitted_name: str,
) -> dict[str, str]:
    """Insert one draft and one submitted document for testing.

    Args:
        user_id: User ID to associate with the drafts
        draft_name: Name for the draft document
        submitted_name: Name for the submitted document

    Returns:
        Dict with the inserted IDs: {"draft_id": str, "submitted_id": str}
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
            "attributes_markdown": "### presence\\n- absent: a\\n- present: b\\n- indeterminate: c\\n",
        },
        "generated_json": None,
        "status": "draft",
        "action_log": [],
    }

    gen_json = await generate_valid_generated_json(submitted_name)
    submitted_doc = {
        "_id": submitted_oid,
        "user_id": user_id,
        "name": submitted_name,
        "created_at": now,
        "updated_at": now,
        "inputs": {
            "description": f"Submitted description for {submitted_name}.",
            "synonyms": ["beta"],
            "attributes_markdown": "### presence\\n- absent: a\\n- present: b\\n- indeterminate: c\\n",
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


async def seed_comment(
    *,
    reference_type: str,
    reference_id: str,
    user_id: int,
    user_name: str,
    content: str,
    parent_id: str | None = None,
    user_avatar_url: str | None = None,
) -> str:
    """Create a test comment in the database.

    Args:
        reference_type: Type of reference ("finding_model" or "draft")
        reference_id: ID of the referenced object (OIFM_ID for finding models, ObjectId for drafts)
        user_id: User ID of comment author
        user_name: Username of comment author
        content: Comment content
        parent_id: Optional parent comment ID for replies
        user_avatar_url: Optional user avatar URL

    Returns:
        Comment ID as string
    """
    from uuid import uuid4

    client: Any = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db["comment_threads"]

    now = datetime.now(UTC)
    comment_id = str(uuid4())

    # Create the comment document
    comment_doc = {
        "id": comment_id,
        "user_id": user_id,
        "user_name": user_name,
        "user_avatar_url": user_avatar_url or f"https://github.com/{user_name}.png?size=40",
        "content": content,
        "created_at": now,
        "replies": [],
    }

    if parent_id:
        # Add as a reply to existing comment
        await col.update_one(
            {"reference_type": reference_type, "reference_id": reference_id, "comments.id": parent_id},
            {"$push": {"comments.$.replies": comment_doc}},
        )
    else:
        # Use upsert to match backend logic - thread identified by reference_type/reference_id
        await col.update_one(
            {"reference_type": reference_type, "reference_id": reference_id},
            {
                "$push": {"comments": comment_doc},
                "$inc": {"comment_count": 1},
                "$set": {"updated_at": now},
                "$setOnInsert": {
                    "_id": ObjectId(),  # Auto-generate an ObjectId like backend does
                    "reference_type": reference_type,
                    "reference_id": reference_id,
                    "created_at": now,
                    "reported_count": 0,
                },
            },
            upsert=True,
        )

    await db.command("ping")  # Ensure write is committed
    client.close()

    return comment_id


async def cleanup_test_data(user_id: int, draft_name: str | None = None) -> None:
    """Clean up test data from the database.

    Args:
        user_id: User ID to clean up data for
        draft_name: Optional specific draft name to clean up
    """
    client: Any = AsyncIOMotorClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    col = db["finding_model_drafts"]

    if draft_name:
        await col.delete_many({"user_id": user_id, "name": draft_name})
    else:
        await col.delete_many({"user_id": user_id})

    await db.command("ping")
    client.close()


def collect_console_errors(page: Page) -> tuple[list[str], list[str]]:
    """Set up console error collection for a page.

    Args:
        page: Playwright page instance

    Returns:
        Tuple of (errors, warnings) lists that will be populated during page usage
    """
    errors: list[str] = []
    warnings: list[str] = []

    def on_console(msg: ConsoleMessage) -> None:
        text = msg.text or ""
        if msg.type == "error":
            errors.append(text)
        elif msg.type == "warning":
            warnings.append(text)

    page.on("console", on_console)  # type: ignore[arg-type]

    def on_page_error(err: Exception) -> None:  # noqa: ANN001 - third-party signature
        errors.append(str(err))

    page.on("pageerror", on_page_error)  # type: ignore[arg-type]
    return errors, warnings


async def verify_model_display(page: Page, *, has_ids: bool = False, has_json: bool = False) -> None:
    """Verify model display elements are present on the page.

    Args:
        page: Playwright page instance
        has_ids: Whether ID elements should be visible
        has_json: Whether JSON accordion should be visible
    """
    from playwright.async_api import expect

    # Check for model display elements (flexible for different page types)
    # Look for either creation completion or draft view headers
    model_ready_header = page.locator("h2:has-text('Your Finding Model is Ready!')")
    draft_view_header = page.locator("h1, h2").filter(has_text=re.compile(r"UI Test|Test|Finding Model"))

    # Try to find either type of header
    if await model_ready_header.count() > 0:
        await expect(model_ready_header).to_be_visible(timeout=15000)
    else:
        await expect(draft_view_header.first).to_be_visible(timeout=15000)

    # Check for model content (more flexible selectors and longer timeouts)
    model_name = page.locator("h1, h2").filter(has_text=re.compile(r"UI Test|Test"))
    model_desc = page.locator("p").first
    attributes_section = page.locator("h3:has-text('Attributes'), h4:has-text('Attributes')")

    await expect(model_name).to_be_visible(timeout=10000)
    await expect(model_desc).to_be_visible(timeout=10000)
    await expect(attributes_section).to_be_visible(timeout=10000)

    # Check for IDs if expected
    id_labels = page.locator("text=ID:")
    if has_ids:
        assert await id_labels.count() > 0, "Expected ID labels to be visible"
    else:
        await expect(id_labels).to_have_count(0)

    # Check for JSON accordion if expected
    json_accordion = page.locator("#finding-model-json")
    if has_json:
        await expect(json_accordion).to_be_visible()
    else:
        await expect(json_accordion).to_have_count(0)


async def verify_no_console_errors(
    errors: list[str], warnings: list[str], allowed_patterns: list[str] | None = None
) -> None:
    """Verify no problematic console errors occurred.

    Args:
        errors: List of console errors collected
        warnings: List of console warnings collected
        allowed_patterns: Optional list of error patterns to ignore
    """
    bad_keywords = [
        "Flowbite",
        "Modal",
        "not been initialized",
        "does not exist",
        "Alpine Expression Error",
        "SyntaxError",
        "Unexpected keyword",
    ]

    allowed_patterns = allowed_patterns or []

    # Filter out allowed patterns
    filtered_errors = []
    for error in errors:
        is_allowed = any(pattern in error for pattern in allowed_patterns)
        if not is_allowed and any(keyword.lower() in error.lower() for keyword in bad_keywords):
            filtered_errors.append(error)

    assert not filtered_errors, f"Console errors found: {filtered_errors}"


async def navigate_to_create_page(page: Page) -> None:
    """Navigate to the create finding model page (requires authentication first).

    Args:
        page: Playwright page instance
    """
    await page.goto("http://localhost:8000/create-finding-model")
    await page.wait_for_load_state("networkidle")


async def navigate_to_profile_page(page: Page) -> None:
    """Navigate to the profile page (requires authentication first).

    Args:
        page: Playwright page instance
    """
    await page.goto("http://localhost:8000/profile")
    await page.wait_for_load_state("networkidle")


async def wait_for_htmx_to_settle(page: Page, timeout: int = 5000) -> None:
    """Wait for HTMX requests to complete and DOM to settle.

    This replaces arbitrary wait_for_timeout() calls with proper HTMX detection.
    """
    # Wait for any active HTMX requests to complete
    await page.wait_for_function("() => !document.body.classList.contains('htmx-request')", timeout=timeout)
    # Additional small wait for DOM updates
    await page.wait_for_timeout(100)


async def wait_for_htmx_swap(page: Page, expected_selector: str, timeout: int = 10000) -> None:
    """Wait for HTMX swap to complete and expected content to appear.

    This is the preferred way to wait after HTMX operations.

    Args:
        page: Playwright page instance
        expected_selector: CSS selector for element that should appear after swap
        timeout: Timeout in milliseconds
    """
    # Wait for HTMX to finish
    await wait_for_htmx_to_settle(page, timeout=timeout)

    # Wait for expected content
    await page.wait_for_selector(expected_selector, state="visible", timeout=timeout)


async def wait_for_ai_completion_and_swap(
    page: Page, button_text_prefix: str, expected_element: str, timeout: int = 60000
) -> None:
    """Wait for AI button to complete processing and HTMX to swap new content.

    CRITICAL: All workflow content swaps happen in #main-content. The expected_element
    should be relative to #main-content.

    Args:
        page: Playwright page instance
        button_text_prefix: Prefix of button text (e.g., "Generat" for "Generate Description")
        expected_element: CSS selector for element expected after swap (will be prefixed with #main-content)
        timeout: Total timeout in milliseconds for AI operation
    """
    # Wait for button to finish processing (no more "...ing" text)
    await page.wait_for_function(
        f"""() => {{
            const buttons = Array.from(document.querySelectorAll('#main-content button'));
            const processingButtons = buttons.filter(btn =>
                btn.textContent &&
                btn.textContent.includes('{button_text_prefix}') &&
                (btn.textContent.includes('ing...') || btn.textContent.includes('ing'))
            );
            return processingButtons.length === 0;
        }}""",
        timeout=timeout,
    )

    # Wait for HTMX to settle (no active requests)
    await wait_for_htmx_to_settle(page, timeout=5000)

    # Wait for expected content to appear in main-content
    full_selector = f"#main-content {expected_element}"
    await page.wait_for_selector(full_selector, state="visible", timeout=5000)


async def wait_for_step_container_update(page: Page, marker_selector: str, timeout: int = 10000) -> None:
    """Wait for #main-content to be updated with new content.

    Args:
        page: Playwright page instance
        marker_selector: CSS selector for element that indicates the new step/content
        timeout: Timeout in milliseconds
    """
    await page.wait_for_selector(f"#main-content {marker_selector}", state="visible", timeout=timeout)


async def wait_for_alpine_ready(page: Page, timeout: int = 10000) -> None:
    """Wait for Alpine.js to be initialized and ready.

    Args:
        page: Playwright page instance
        timeout: Timeout in milliseconds
    """
    import contextlib

    try:
        await page.wait_for_function("""() => window.Alpine && window.Alpine.started""", timeout=timeout)
    except Exception:
        # Alpine might not be available on all pages, or might have a different initialization
        # Try to wait for at least the basic Alpine object
        with contextlib.suppress(Exception):
            await page.wait_for_function("""() => window.Alpine""", timeout=2000)


async def wait_for_draft_redirect(page: Page, timeout: int = 15000) -> str | None:
    """Wait for and detect if HTMX processed a 303 redirect to draft page.

    This helper detects when step 2 "Check for Similar" results in no similar
    models found, causing a 303 redirect to the draft edit page.

    Args:
        page: Playwright page instance
        timeout: Timeout in milliseconds

    Returns:
        Draft ID if redirected to draft page, None if stayed on creation page
    """
    try:
        # Wait for HTMX to finish processing
        await wait_for_htmx_to_settle(page, timeout=timeout)

        # Check if we were redirected to a draft page
        current_url = page.url
        if "/drafts/" in current_url:
            # Extract draft ID from URL like /drafts/{id}?mode=edit
            import re

            match = re.search(r"/drafts/([^/?]+)", current_url)
            return match.group(1) if match else None

        return None
    except Exception:
        return None


async def wait_for_mode_switch(page: Page, expected_mode: str, timeout: int = 10000) -> None:
    """Wait for edit/view mode switching to complete on unified draft page.

    Args:
        page: Playwright page instance
        expected_mode: Either "edit" or "view"
        timeout: Timeout in milliseconds
    """
    if expected_mode == "edit":
        # Wait for edit form elements to appear
        await page.wait_for_selector("textarea#description", state="visible", timeout=timeout)
        await page.wait_for_selector("button:has-text('Update & Preview')", state="visible", timeout=timeout)
    else:  # view mode
        # Wait for model display elements to appear
        # Could be either creation workflow completion or draft preview
        model_ready = page.locator("h2:has-text('Your Finding Model is Ready!')")

        if await model_ready.count() > 0:
            await page.wait_for_selector(
                "h2:has-text('Your Finding Model is Ready!')", state="visible", timeout=timeout
            )
        else:
            await page.wait_for_selector("h2", state="visible", timeout=timeout)

        # Submit button should be visible in view mode
        await page.wait_for_selector("button:has-text('Submit Draft')", state="visible", timeout=timeout)


async def wait_for_step_container_content(page: Page, expected_content_selector: str, timeout: int = 10000) -> None:
    """Wait for specific content to appear in #main-content after HTMX swap.

    This is a more specific version of wait_for_htmx_swap that focuses on
    the step container used in the creation workflow.

    Args:
        page: Playwright page instance
        expected_content_selector: CSS selector for content expected in #main-content
        timeout: Timeout in milliseconds
    """
    # First wait for HTMX to settle
    await wait_for_htmx_to_settle(page, timeout=timeout)

    # Then wait for the specific content within main content container
    full_selector = f"#main-content {expected_content_selector}"
    await page.wait_for_selector(full_selector, state="visible", timeout=timeout)


async def wait_for_creation_workflow_transition(
    page: Page, button_text: str, expected_outcome_selector: str, timeout: int = 60000
) -> str:
    """Wait for creation workflow transitions that might redirect or swap content.

    This helper handles the complex logic of waiting for workflow transitions
    that can either result in HTMX content swaps or redirects to draft pages.

    Args:
        page: Playwright page instance
        button_text: Text of the button being clicked (for debugging)
        expected_outcome_selector: Selector for content that should appear after transition
        timeout: Total timeout for the operation

    Returns:
        "swapped" if content was swapped in place, "redirected" if redirected to draft page
    """
    # Wait for AI operation to complete (button stops showing "...ing" text)
    await page.wait_for_function(
        f"""() => {{
            const buttons = Array.from(document.querySelectorAll('button'));
            const processingButtons = buttons.filter(btn =>
                btn.textContent &&
                btn.textContent.includes('{button_text}') &&
                (btn.textContent.includes('ing...') || btn.textContent.includes('ing'))
            );
            return processingButtons.length === 0;
        }}""",
        timeout=timeout,
    )

    # Wait a moment for HTMX to process any redirects
    await page.wait_for_timeout(500)

    # Check if we were redirected to draft page
    current_url = page.url
    if "/drafts/" in current_url:
        # We were redirected - wait for draft page content
        await page.wait_for_selector(expected_outcome_selector, state="visible", timeout=5000)
        return "redirected"
    else:
        # Content was swapped - wait for it to appear in step container
        await wait_for_step_container_content(page, expected_outcome_selector, timeout=5000)
        return "swapped"
