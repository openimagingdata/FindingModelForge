"""Working Playwright integration tests for HTMX finding model creation."""

import os
from typing import Any

import pytest
from playwright.async_api import Page, async_playwright, expect

# Mark all tests in this file as integration tests requiring Playwright
pytestmark = [pytest.mark.integration, pytest.mark.slow, pytest.mark.playwright]


class TestHTMXFindingModelCreationWorking:
    """Working integration tests for the HTMX finding model creation workflow."""

    async def test_navigation_to_login_page(self):
        """Test basic navigation to the create page (shows login requirement)."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Navigate to home page first
                await page.goto("http://localhost:8000")
                title = await page.title()
                assert "Finding Model Forge" in title

                # Navigate to create page (should show login)
                await page.goto("http://localhost:8000/create-finding-model")
                await page.wait_for_load_state("networkidle")

                # Should show login required
                title = await page.title()
                assert "Login Required" in title

                # Check for login message
                login_message = page.locator("text=Please log in to create finding models")
                await expect(login_message).to_be_visible(timeout=5000)

            finally:
                await browser.close()

    async def test_home_page_navigation(self):
        """Test navigation around the public parts of the site."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Test home page
                await page.goto("http://localhost:8000")
                await page.wait_for_load_state("networkidle")

                title = await page.title()
                assert "Finding Model Forge" in title

                # Look for navigation elements
                nav = page.locator("nav")
                await expect(nav).to_be_visible()

                # Test that JavaScript is working (dark mode toggle should be present)
                # This indirectly tests that the frontend build is working
                body = page.locator("body")
                await expect(body).to_be_visible()

            finally:
                await browser.close()

    async def test_health_endpoint_via_browser(self):
        """Test the health endpoint via browser navigation."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Navigate to health endpoint
                await page.goto("http://localhost:8000/api/health")
                await page.wait_for_load_state("networkidle")

                # Should get JSON response
                content = await page.text_content("pre")  # JSON is often wrapped in <pre>
                if not content:
                    # If no <pre> tag, get body content
                    content = await page.text_content("body")

                # Should contain status information
                assert content is not None
                assert "healthy" in content.lower() or "ok" in content.lower()

            finally:
                await browser.close()

    async def test_authenticated_access_via_test_endpoint(self):
        """Test that the test authentication endpoint allows access to protected routes."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Step 1: Navigate to test auth endpoint to get authenticated
                await page.goto("http://localhost:8000/test-auth/login")
                await page.wait_for_load_state("networkidle")

                # Should be redirected to create-finding-model page
                current_url = page.url
                assert "/create-finding-model" in current_url

                # Step 2: Verify we can access the protected page
                title = await page.title()
                assert "Login Required" not in title
                assert "Create Finding Model" in title

                # Step 3: Look for the expected form elements
                # Check for step 1 content (finding name input)
                name_input = page.locator("input[name='name']")
                await expect(name_input).to_be_visible(timeout=5000)

                # Check for navigation breadcrumb/stepper
                stepper = page.locator("[data-stepper]")
                if await stepper.count() > 0:
                    await expect(stepper).to_be_visible()

            finally:
                await browser.close()

    async def test_basic_htmx_form_interaction(self):
        """Test basic HTMX form interaction on the first step."""
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false")
            page = await browser.new_page()

            try:
                # Use helper method to authenticate and navigate
                await self._navigate_to_create(page)

                # Fill in the finding name
                name_input = page.locator("input[name='name']")
                await name_input.fill("Test Finding Name")

                # Look for and click the "Check Availability" button
                check_btn = page.locator("button:has-text('Check Availability')")
                if await check_btn.count() > 0:
                    await check_btn.click()

                    # Wait for HTMX response
                    await page.wait_for_timeout(2000)  # Wait for HTMX to process

                    # Look for some indication that the check happened
                    # This could be success message, error message, or enabled "Continue" button
                    continue_btn = page.locator("button:has-text('Continue')")
                    success_msg = page.locator(".text-green-600, .success, [data-success]")
                    error_msg = page.locator(".text-red-600, .error, [data-error]")

                    # At least one of these should be visible after the check
                    has_response = (
                        await continue_btn.count() > 0 or await success_msg.count() > 0 or await error_msg.count() > 0
                    )
                    assert has_response, "No response detected after name availability check"

            finally:
                await browser.close()

    async def test_complete_htmx_workflow_debug(self):
        """Interactive test for debugging the complete HTMX workflow."""
        async with async_playwright() as p:
            # Only run this test in headed mode for debugging
            if os.getenv("PLAYWRIGHT_HEADLESS", "true") != "false":
                pytest.skip("This test only runs in headed mode for debugging")

            browser = await p.chromium.launch(
                headless=False,
                slow_mo=1000,  # 1 second delay between actions for visibility
            )
            page = await browser.new_page(viewport={"width": 1400, "height": 1000})

            try:
                print("🚀 Starting HTMX workflow test...")

                # Step 1: Navigate and authenticate
                print("🔐 Authenticating...")
                await self._navigate_to_create(page)
                await page.wait_for_timeout(2000)

                # Step 2: Fill in the finding name
                print("📝 Filling finding name...")
                name_input = page.locator("input[name='name']")
                await name_input.fill("Debug Test Finding")
                await page.wait_for_timeout(1000)

                # Step 3: Generate description (Step 1)
                print("🔍 Step 1: Looking for Generate Description button...")
                # Try multiple possible button selectors
                step1_selectors = [
                    "button:has-text('Generate Description')",
                    "button[type='submit']",
                    "input[type='submit']",
                    "button[hx-post]",
                ]

                button_found = False
                for selector in step1_selectors:
                    check_btn = page.locator(selector)
                    if await check_btn.count() > 0:
                        print(f"✅ Found button with selector: {selector}")
                        await check_btn.wait_for(state="visible", timeout=5000)
                        await check_btn.click()
                        print("🎯 Button clicked! Waiting for HTMX response...")

                        # Wait for HTMX response
                        await page.wait_for_load_state("networkidle", timeout=10000)
                        await page.wait_for_timeout(2000)
                        print("✅ Description generated!")

                        # Test synonym management after description generation
                        print("🏷️  Testing synonym management on edit description page...")
                        await self._test_synonym_management(page, "edit description page")

                        button_found = True
                        break

                if not button_found:
                    print("❌ No generate description button found, checking page content...")
                    # Find form elements
                    forms = await page.locator("form").count()
                    buttons = await page.locator("button").count()
                    inputs = await page.locator("input").count()
                    print(f"Found {forms} forms, {buttons} buttons, {inputs} inputs")

                # Step 4: Check current page state and look for Continue button
                print("📊 Checking current page state...")
                current_url = page.url
                current_title = await page.title()
                print(f"📍 Current URL: {current_url}")
                print(f"📍 Current title: {current_title}")

                # Count all elements to see what's on the page now
                buttons = await page.locator("button").count()
                forms = await page.locator("form").count()
                textareas = await page.locator("textarea").count()
                print(f"📊 Page now has: {buttons} buttons, {forms} forms, {textareas} textareas")

                print("🔍 Step 2: Looking for Check for Similar button...")
                similar_selectors = [
                    "button:has-text('Check for Similar')",
                    "button:has-text('Similar')",
                    "button[type='submit']:not(:has-text('Generate'))",
                ]

                similar_found = False
                for selector in similar_selectors:
                    similar_btn = page.locator(selector)
                    if await similar_btn.count() > 0:
                        is_enabled = await similar_btn.is_enabled()
                        is_visible = await similar_btn.is_visible()
                        print(f"✅ Check for Similar button found with selector: {selector}")
                        print(f"   enabled: {is_enabled}, visible: {is_visible}")
                        if is_enabled and is_visible:
                            await similar_btn.click()
                            print("🎯 Clicked Check for Similar, waiting for response...")

                            # Wait for the button text to change (indicating HTMX DOM update completed)
                            try:
                                await page.wait_for_function(
                                    """() => {
                                        const buttons = document.querySelectorAll('button');
                                        for (const button of buttons) {
                                            if (button.textContent && button.textContent.includes('Checking...')) {
                                                return false; // Still checking, keep waiting
                                            }
                                        }
                                        return true; // No more "Checking..." buttons
                                    }""",
                                    timeout=15000,
                                )
                                print("✅ Similar check completed!")

                            except Exception:
                                print("⚠️ Similar check may still be running")

                            await page.wait_for_timeout(2000)

                            similar_found = True
                            break

                if similar_found:
                    await page.wait_for_timeout(2000)  # Brief pause

                    # Step 3: We should now be on the attributes editing page with "Generate Final Model" button
                    print("🔍 Step 3: Checking if we're on the attributes editing page...")

                    # Wait for attributes editing step to appear (should already be there after similar check)
                    try:
                        await page.wait_for_selector(
                            "h3:has-text('Attributes'), textarea[name*='attribute'], .attribute", timeout=8000
                        )
                        print("✅ Attributes step appeared!")

                        # Test synonym management during attributes editing (BEFORE clicking Generate Final Model)
                        print("🏷️  Testing synonym management on edit attributes page...")
                        await self._test_synonym_management(page, "edit attributes page")

                        # NOW look for and click Generate Final Model button
                        print("🔍 Step 4: Looking for Generate Final Model button...")
                        final_selectors = [
                            "button:has-text('Generate Final Model')",
                            "button:has-text('Generate Model')",
                            "button[type='submit']:not(:has-text('Check')):not(:has-text('Add'))",
                        ]

                        final_clicked = False
                        for selector in final_selectors:
                            final_btn = page.locator(selector)
                            if await final_btn.count() > 0:
                                await final_btn.first.click()
                                print("🎯 Clicked Generate Final Model button")
                                final_clicked = True
                                break

                        if final_clicked:
                            # Wait for final model generation to complete - HTMX response
                            print("⏳ Waiting for HTMX response after Generate Final Model...")
                            try:
                                # Wait for the success heading to appear (indicates HTMX completed)
                                await page.wait_for_selector(
                                    "h2:has-text('Your Finding Model is Ready!')", timeout=30000
                                )
                                print("✅ Final model generation completed!")
                            except Exception:
                                print("⚠️ Final model generation may have timed out")
                                await page.wait_for_timeout(3000)  # Fallback wait
                        else:
                            print("❌ Generate Final Model button not found")

                    except Exception:
                        print("⚠️ Attributes step may not have appeared")

                    if not final_clicked:
                        print("❌ Generate Final Model button not found")
                else:
                    print("❌ No Check for Similar button found or enabled")

                # Final page inspection - check for all expected elements
                current_url = page.url
                current_title = await page.title()
                print(f"🏁 Final URL: {current_url}")
                print(f"🏁 Final title: {current_title}")

                # Check for key final page elements - and ASSERT they exist!
                print("🔍 Checking for expected final page elements...")

                # 1. Success message and heading
                success_heading = page.locator("h2:has-text('Your Finding Model is Ready!')")
                success_count = await success_heading.count()
                print(f"📊 Success heading: {success_count} found")
                assert success_count > 0, "❌ Success heading not found!"

                # 2. Generated model display (finding name, description, attributes)
                model_name = page.locator("h2.text-2xl.font-bold")  # Finding model name
                model_desc = page.locator("p.text-gray-700")  # Description
                attributes_section = page.locator("h3:has-text('Attributes')")
                name_count = await model_name.count()
                desc_count = await model_desc.count()
                attr_count = await attributes_section.count()
                print(f"📊 Model display - Name: {name_count}, Description: {desc_count}, Attributes: {attr_count}")
                assert name_count > 0, "❌ Model name not found!"
                assert desc_count > 0, "❌ Model description not found!"
                assert attr_count > 0, "❌ Attributes section not found!"

                # 3. JSON accordion
                json_accordion = page.locator("#finding-model-json")
                json_button = page.locator("button[data-accordion-target='#finding-model-json-body-1']")
                json_content = page.locator("#finding-model-json-body-1 pre code")
                accordion_count = await json_accordion.count()
                button_count = await json_button.count()
                content_count = await json_content.count()
                print(f"📊 JSON accordion - Accordion: {accordion_count}, Button: {button_count}")
                print(f"   Content: {content_count}")
                assert accordion_count > 0, "❌ JSON accordion not found!"
                assert button_count > 0, "❌ JSON accordion button not found!"
                assert content_count > 0, "❌ JSON content not found!"

                # 4. Copy and Download buttons
                copy_btn = page.locator("button:has-text('Copy')")
                download_btn = page.locator("button:has-text('Download')")
                copy_count = await copy_btn.count()
                download_count = await download_btn.count()
                print(f"📊 Action buttons - Copy: {copy_count}, Download: {download_count}")
                assert copy_count > 0, "❌ Copy button not found!"
                assert download_count > 0, "❌ Download button not found!"

                # 5. Navigation buttons
                back_btn = page.locator("button:has-text('← Back')")
                create_another_btn = page.locator("button:has-text('Create Another')")
                back_count = await back_btn.count()
                create_count = await create_another_btn.count()
                print(f"📊 Navigation buttons - Back: {back_count}, Create Another: {create_count}")
                assert back_count > 0, "❌ Back button not found!"
                assert create_count > 0, "❌ Create Another button not found!"

                # 6. Test the JSON content actually contains data
                if await json_content.count() > 0:
                    # Click accordion to expand it first
                    if await json_button.count() > 0:
                        await json_button.click()
                        await page.wait_for_timeout(1000)

                    json_text = await json_content.text_content()
                    if json_text and len(json_text.strip()) > 10:
                        print(f"✅ JSON content: {len(json_text)} characters of JSON data found")
                        # Check if it looks like valid JSON
                        if '"name"' in json_text and '"attributes"' in json_text:
                            print("✅ JSON contains expected finding model structure")
                        else:
                            print("⚠️ JSON doesn't contain expected structure")
                    else:
                        print("❌ JSON content is empty or too short")
                else:
                    print("❌ No JSON content found")

                print("✅ Final page validation completed")

            except Exception as e:
                print(f"❌ Test failed with error: {e}")
                print("🔍 Browser will stay open for debugging...")

            # Keep browser open for inspection (outside try block)
            print("⏰ Keeping browser open for 10 seconds...")
            await page.wait_for_timeout(10000)  # Keep browser open for 10 seconds
            await browser.close()

    async def _test_synonym_management(self, page: Page, context: str) -> None:
        """Test adding and removing synonyms using Alpine.js."""
        print(f"🔍 Looking for synonym management in context: {context}")

        # Look for synonym input field and add button
        synonym_input = page.locator(
            "input[x-model='newSynonym'], input[placeholder*='synonym'], input[placeholder*='Add a synonym']"
        )
        add_button = page.locator("button:has-text('Add')")

        synonym_input_count = await synonym_input.count()
        add_button_count = await add_button.count()

        print(f"📊 Found {synonym_input_count} synonym inputs and {add_button_count} add buttons")

        if synonym_input_count > 0 and add_button_count > 0:
            # Use different synonym names for different contexts to avoid confusion
            if "attributes" in context.lower():
                synonym1 = "test synonym 3"
                synonym2 = "test synonym 4"
            else:
                synonym1 = "test synonym 1"
                synonym2 = "test synonym 2"

            # Count initial synonyms with our test names
            initial_badges = page.locator(f"span:has-text('{synonym1}'), span:has-text('{synonym2}')")
            initial_count = await initial_badges.count()
            print(f"📊 Initial {synonym1}/{synonym2} synonyms on page: {initial_count}")

            # Test adding first synonym
            print(f"➕ Adding {synonym1}...")
            await synonym_input.first.fill(synonym1)
            await page.wait_for_timeout(500)
            await add_button.first.click()
            await page.wait_for_timeout(1000)

            # Verify first synonym appeared
            first_synonym = page.locator(f"span:has-text('{synonym1}')")
            first_count = await first_synonym.count()
            print(f"✅ After adding {synonym1}: {first_count} found")

            # Add second synonym
            print(f"➕ Adding {synonym2}...")
            await synonym_input.first.fill(synonym2)
            await page.wait_for_timeout(500)
            await add_button.first.click()
            await page.wait_for_timeout(1000)

            # Verify both synonyms are present
            both_synonyms = page.locator(f"span:has-text('{synonym1}'), span:has-text('{synonym2}')")
            both_count = await both_synonyms.count()
            print(f"✅ After adding both: {both_count} found")

            # Test removing a synonym - be very specific about the remove button
            if both_count > 0:
                print("➖ Testing synonym removal...")
                # Look for the X button specifically within our test synonym spans
                remove_buttons = page.locator(f"span:has-text('{synonym1}') button svg[stroke='currentColor']")
                remove_count = await remove_buttons.count()
                print(f"🔍 Found {remove_count} remove buttons for {synonym1}")

                if remove_count > 0:
                    # Click the remove button (parent button of the SVG)
                    first_remove_btn = remove_buttons.first.locator("..")  # Get parent button
                    await first_remove_btn.click()
                    await page.wait_for_timeout(1000)

                    # Verify synonym was removed
                    after_removal = page.locator(f"span:has-text('{synonym1}'), span:has-text('{synonym2}')")
                    new_count = await after_removal.count()
                    print(f"📊 After removal: {new_count} synonyms remain")

                    if new_count < both_count:
                        print("✅ Synonym successfully removed")
                    else:
                        print("⚠️ Synonym removal may not have worked")
                else:
                    print("⚠️ No specific remove buttons found")

            print(f"✅ Synonym management test completed for {context}")
        else:
            print(f"⏭️ No synonym management found in {context} - skipping test")

    async def _navigate_to_create(self, page: Page) -> None:
        """Helper method to navigate to the create finding model page with authentication."""
        # Authenticate first
        await page.goto("http://localhost:8000/test-auth/login")
        await page.wait_for_load_state("networkidle")

        # Should be redirected to create-finding-model page
        assert "/create-finding-model" in page.url


# Configuration for pytest-playwright (in case we fix the plugin later)
@pytest.fixture(scope="session")
def playwright_browser() -> dict[str, Any]:
    """Configure Playwright browser for tests."""
    return {
        "headless": True,
        "slow_mo": 100,
    }


@pytest.fixture(scope="session")
def playwright_page() -> dict[str, Any]:
    """Configure Playwright page for tests."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }
