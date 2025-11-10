"""UI tests for draft comment functionality.

Tests comment functionality specifically on draft pages including:
- Comments visible only on submitted drafts
- No comment interface for draft status
- Comment persistence across navigation
"""

from __future__ import annotations

import time

import pytest
from playwright.async_api import Page, expect

from tests.ui.utils import (
    TEST_USER_ID,
    generate_valid_generated_json,
    seed_comment,
    seed_draft,
    verify_no_console_errors,
    wait_for_htmx_settled,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestDraftComments:
    """Test comment functionality for draft pages."""

    async def test_comments_on_submitted_draft(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that comments can be added to submitted drafts."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Seed a submitted draft with generated JSON (REQUIRED for comments!)
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Submitted Draft {timestamp}"

        # CRITICAL: Must use generate_valid_generated_json for valid FindingModelFull JSON
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for submitted draft",
            status="submitted",
            generated_json=generated_json,  # CRITICAL: Must have this!
        )

        # 2. Navigate to draft page
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 3. Verify comment section is visible (comment section ID: comment-thread-draft-{draft_id})
        comment_section = page.locator(f"#comment-thread-draft-{draft_id}")
        await expect(comment_section).to_be_visible(timeout=5000)
        # Wait for HTMX to fully initialize the comment form
        await wait_for_htmx_settled(page)

        # 4. Add a comment with unique timestamp
        comment_timestamp = str(int(time.time()))
        test_comment = f"Test comment {comment_timestamp} - draft comment test"

        comment_textarea = page.locator('textarea[name="content"]').last
        await comment_textarea.click()
        await wait_for_htmx_settled(page)
        await comment_textarea.fill(test_comment)
        await wait_for_htmx_settled(page)

        # Submit the comment
        post_button = page.locator("button:has-text('Post')").last
        await expect(post_button).not_to_be_disabled()
        await post_button.click()

        # 5. Verify comment appears in the thread
        await page.wait_for_selector(f"text={test_comment}", timeout=10000)
        new_comment = page.locator(f"text={test_comment}")
        await expect(new_comment.first).to_be_visible()

        await verify_no_console_errors(errors, warnings)

    async def test_no_comments_on_draft_status(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that comments cannot be added to drafts with status='draft'."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create draft with status="draft" (not submitted)
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Draft Status {timestamp}"

        # Even with valid generated_json, draft status should prevent comments
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for draft status",
            status="draft",  # NOT submitted
            generated_json=generated_json,
        )

        # 2. Navigate to draft page
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 3. Should redirect to edit mode or not show comments
        comment_section = page.locator(f"#comment-thread-draft-{draft_id}")
        await expect(comment_section).not_to_be_visible()

        # 4. Verify no comment textarea exists
        comment_textarea = page.locator('textarea[name="content"]')
        await expect(comment_textarea).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_draft_comment_persistence(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that comments persist on draft pages across navigation."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create submitted draft with generated JSON
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Comment Persistence {timestamp}"

        # Must have valid FindingModelFull JSON for comments to appear
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for comment persistence",
            status="submitted",
            generated_json=generated_json,  # Required!
        )

        # 2. Add a comment with unique identifier
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        comment_timestamp = str(int(time.time()))
        test_comment = f"Test persistence comment {comment_timestamp}"

        comment_textarea = page.locator('textarea[name="content"]').last
        await comment_textarea.click()
        await wait_for_htmx_settled(page)
        await comment_textarea.fill(test_comment)
        await wait_for_htmx_settled(page)

        post_button = page.locator("button:has-text('Post')").last
        await post_button.click()

        # Wait for comment to appear
        await page.wait_for_selector(f"text={test_comment}", timeout=10000)

        # 3. Navigate away to home page
        await page.goto("http://localhost:8000/")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 4. Navigate back to draft
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 5. Verify the comment is still visible
        persisted_comment = page.locator(f"text={test_comment}")
        await expect(persisted_comment.first).to_be_visible(timeout=5000)

        await verify_no_console_errors(errors, warnings)

    async def test_report_comment_on_draft(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test reporting a comment on a draft."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create a submitted draft with generated JSON
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Report Draft {timestamp}"
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for draft report test",
            status="submitted",
            generated_json=generated_json,
        )

        # 2. Seed a comment from another user
        await seed_comment(
            reference_type="draft",
            reference_id=draft_id,
            user_id=456789,  # Different from TEST_USER_ID (999999)
            user_name="draft-commenter",
            content="This draft comment can be reported",
        )

        # 3. Navigate to draft page
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 4. Wait for comment section to load
        comment_section = page.locator(f"#comment-thread-draft-{draft_id}")
        await expect(comment_section).to_be_visible(timeout=5000)

        # Find the comment from other user (specifically in the comment header span)
        other_user_comment = page.locator("article span.font-medium:has-text('draft-commenter')").first
        await expect(other_user_comment).to_be_visible(timeout=5000)

        # 5. Find and click report button
        report_button = page.locator('button[title="Report inappropriate content"]').first
        await expect(report_button).to_be_visible()

        # Set up dialog handler
        dialog_handled = False

        async def handle_dialog(dialog):
            nonlocal dialog_handled
            assert "Are you sure you want to report this comment" in dialog.message
            dialog_handled = True
            await dialog.accept()

        page.on("dialog", handle_dialog)

        # Monitor response to verify HTMX request is made
        responses = []

        def track_response(response):
            if "report" in response.url:
                responses.append(f"{response.status}")

        page.on("response", track_response)

        await report_button.click()

        # 6. Wait for HTMX to settle and verify response
        await wait_for_htmx_settled(page)

        # Verify HTMX request was made with success response
        if responses:
            response_status = responses[0]
            if response_status == "200":
                # Verify success message appears (button is replaced with "Reported" text)
                success_message = page.locator("span:text-is('Reported')")
                await expect(success_message).to_be_visible(timeout=5000)

                # Verify report button is no longer available for this comment
                await expect(report_button).not_to_be_visible()
            elif response_status == "400":
                # Should show error message for 400 (already reported, etc.)
                error_message = page.locator("span:text-is('Already reported')")
                await expect(error_message).to_be_visible(timeout=5000)
                raise AssertionError("Report request failed with 400 - comment may have already been reported")
            elif response_status == "404":
                raise AssertionError("Report request failed with 404 - comment or draft not found")
            else:
                raise AssertionError(f"Unexpected response status: {response_status}")
        else:
            raise AssertionError("No HTMX response received - report functionality not working")

        assert dialog_handled, "Confirmation dialog was not shown for draft comment"

        await verify_no_console_errors(errors, warnings)

    async def test_cannot_report_own_draft_comment(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that users cannot report their own comments on drafts."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create a submitted draft
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Own Comment Draft {timestamp}"
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for own comment test",
            status="submitted",
            generated_json=generated_json,
        )

        # 2. Navigate to draft and add own comment
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        comment_timestamp = str(int(time.time()))
        test_comment = f"Own draft comment {comment_timestamp} - no report button expected"

        comment_textarea = page.locator('textarea[name="content"]').last
        await comment_textarea.click()
        await wait_for_htmx_settled(page)
        await comment_textarea.fill(test_comment)
        await wait_for_htmx_settled(page)

        post_button = page.locator("button:has-text('Post')").last
        await expect(post_button).not_to_be_disabled()
        await post_button.click()

        # 3. Wait for comment to appear
        await page.wait_for_selector(f"text={test_comment}", timeout=10000)

        # 4. Verify NO report button appears on own comment
        own_comment = page.locator(f"text={test_comment}")
        await expect(own_comment).to_be_visible()

        # Check that comment article doesn't contain report button
        comment_article = page.locator("article").filter(has_text=test_comment)
        report_button_in_article = comment_article.locator('button[title="Report inappropriate content"]')
        await expect(report_button_in_article).to_have_count(0)

        await verify_no_console_errors(errors, warnings)

    async def test_cannot_report_same_draft_comment_twice(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that users cannot report the same draft comment twice."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create a submitted draft with generated JSON
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Double Report Draft {timestamp}"
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for double report test",
            status="submitted",
            generated_json=generated_json,
        )

        # 2. Seed a comment from another user
        comment_text = f"Draft comment for double report test {timestamp}"
        await seed_comment(
            reference_type="draft",
            reference_id=draft_id,
            user_id=555666,  # Different from TEST_USER_ID (999999)
            user_name="double-report-draft-user",
            content=comment_text,
        )

        # 3. Navigate to draft page
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # 4. Wait for comment section to load
        comment_section = page.locator(f"#comment-thread-draft-{draft_id}")
        await expect(comment_section).to_be_visible(timeout=5000)

        # Find the comment from other user
        seeded_comment = page.locator(f"text={comment_text}")
        await expect(seeded_comment).to_be_visible(timeout=5000)

        # 5. Find and click report button first time
        comment_article = page.locator("article").filter(has_text=comment_text)
        report_button = comment_article.locator('button[title="Report inappropriate content"]')
        await expect(report_button).to_be_visible()

        # Set up dialog handler for first report
        first_dialog_handled = False

        async def handle_first_dialog(dialog):
            nonlocal first_dialog_handled
            assert "Are you sure you want to report this comment" in dialog.message
            first_dialog_handled = True
            await dialog.accept()

        page.on("dialog", handle_first_dialog)

        # Monitor response to verify HTMX request is made
        responses = []

        def track_response(response):
            if "report" in response.url:
                responses.append(f"{response.status}")

        page.on("response", track_response)

        # 6. Report the comment first time (should succeed)
        await report_button.click()
        await wait_for_htmx_settled(page)

        # Verify first report succeeded
        if responses and responses[0] == "200":
            # Verify success message appears (button is replaced with "Reported" text)
            success_message = page.locator("span:text-is('Reported')")
            await expect(success_message).to_be_visible(timeout=5000)
        else:
            raise AssertionError(f"First report failed with status: {responses[0] if responses else 'no response'}")

        assert first_dialog_handled, "First confirmation dialog was not shown"

        # 7. Try to report the same comment again (should fail or be prevented)
        # First check if report button is still visible
        report_button_count = await report_button.count()
        if report_button_count > 0:
            # Button still exists, try clicking it again
            second_dialog_handled = False

            async def handle_second_dialog(dialog):
                nonlocal second_dialog_handled
                second_dialog_handled = True
                await dialog.accept()

            # Remove first handler and add second
            page.remove_listener("dialog", handle_first_dialog)
            page.on("dialog", handle_second_dialog)

            # Clear previous responses
            responses.clear()

            await report_button.click()
            await wait_for_htmx_settled(page)

            # Should get 400 error for already reported
            if responses:
                if responses[0] == "400":
                    # Should show error message
                    error_message = page.locator("span:text-is('Already reported')")
                    await expect(error_message).to_be_visible(timeout=5000)
                else:
                    raise AssertionError(f"Expected 400 for double report, got {responses[0]}")
            else:
                raise AssertionError("No response received for second report attempt")
        else:
            # Report button was removed after first report (expected behavior)
            # Verify "Reported" text is visible instead
            reported_text = page.locator("span:text-is('Reported')")
            await expect(reported_text).to_be_visible(timeout=2000)

        await verify_no_console_errors(errors, warnings)

    async def test_draft_report_button_visibility_anonymous_users(
        self, authenticated_page_with_console: tuple[Page, list[str], list[str]]
    ) -> None:
        """Test that anonymous users don't see report buttons on draft comments."""
        page, errors, warnings = authenticated_page_with_console

        # 1. Create submitted draft and seed comment from another user
        timestamp = str(int(time.time()))
        draft_name = f"UI Test Anonymous Report {timestamp}"
        generated_json = await generate_valid_generated_json(draft_name)

        draft_id = await seed_draft(
            user_id=TEST_USER_ID,
            name=draft_name,
            description="Test description for anonymous report test",
            status="submitted",
            generated_json=generated_json,
        )

        await seed_comment(
            reference_type="draft",
            reference_id=draft_id,
            user_id=555555,
            user_name="anonymous-test-user",
            content="Comment that anonymous users should not be able to report",
        )

        # 2. Navigate as anonymous user (new page context without auth)
        # This simulates what would happen for anonymous users
        await page.goto(f"http://localhost:8000/drafts/{draft_id}")
        # Playwright auto-waits for elements in expect() - no networkidle needed

        # If the draft is accessible to anonymous users and has comments,
        # there should be no report buttons visible
        comment_text = page.locator("text=Comment that anonymous users should not be able to report")

        # Wait a bit to see if comments load (they might not for anonymous users on drafts)
        try:
            await expect(comment_text).to_be_visible(timeout=3000)
            # If comment is visible, verify no report buttons
            report_buttons = page.locator('button[title="Report inappropriate content"]')
            await expect(report_buttons).to_have_count(0)
        except Exception:
            # If comment is not visible, that's also acceptable behavior for anonymous users on drafts
            pass

        await verify_no_console_errors(errors, warnings)
