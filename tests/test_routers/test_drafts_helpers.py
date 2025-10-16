"""Tests for draft router helper functions."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, Request

from app.models import FindingModelDraft, FindingModelInputs, User
from app.routers.drafts.helpers import (
    build_htmx_response_with_oob,
    check_draft_permissions,
    fetch_draft_with_context,
    get_htmx_context,
    is_htmx_request,
    parse_finding_model_from_draft,
    render_draft_edit_content,
    render_draft_preview_content,
)


def test_is_htmx_request_true():
    """Test is_htmx_request returns True when HX-Request header is 'true'."""
    request = Mock(spec=Request)
    request.headers = {"HX-Request": "true"}
    assert is_htmx_request(request) is True


def test_is_htmx_request_false_missing_header():
    """Test is_htmx_request returns False when HX-Request header is missing."""
    request = Mock(spec=Request)
    request.headers = {}
    assert is_htmx_request(request) is False


def test_is_htmx_request_false_wrong_value():
    """Test is_htmx_request returns False when HX-Request header is not 'true'."""
    request = Mock(spec=Request)
    request.headers = {"HX-Request": "false"}
    assert is_htmx_request(request) is False


def test_get_htmx_context_full():
    """Test get_htmx_context with all HTMX headers present."""
    request = Mock(spec=Request)
    request.headers = {"HX-Request": "true", "HX-Current-URL": "https://example.com/drafts/123"}
    request.query_params = {"from": "public"}

    context = get_htmx_context(request)

    assert context["is_htmx"] is True
    assert context["current_url"] == "https://example.com/drafts/123"
    assert context["from_public"] is True


def test_get_htmx_context_minimal():
    """Test get_htmx_context with no HTMX headers."""
    request = Mock(spec=Request)
    request.headers = {}
    request.query_params = {}

    context = get_htmx_context(request)

    assert context["is_htmx"] is False
    assert context["current_url"] == ""
    assert context["from_public"] is False


def test_get_htmx_context_from_not_public():
    """Test get_htmx_context when 'from' param is not 'public'."""
    request = Mock(spec=Request)
    request.headers = {"HX-Request": "true"}
    request.query_params = {"from": "profile"}

    context = get_htmx_context(request)

    assert context["is_htmx"] is True
    assert context["from_public"] is False


# Tests for fetch_draft_with_context


@pytest.mark.asyncio
async def test_fetch_draft_with_context_success():
    """Test fetch_draft_with_context returns draft and author when found."""
    draft_service = AsyncMock()
    draft_dict = {
        "_id": "507f1f77bcf86cd799439011",
        "id": "507f1f77bcf86cd799439011",
        "user_id": 123,
        "name": "Test Draft",
        "status": "draft",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "inputs": {"description": "Test description", "synonyms": [], "attributes_markdown": "## Test\n- test: value"},
        "generated_json": None,
        "action_log": [],
        "author_name": "Test User",
        "author_username": "testuser",
    }
    draft_service.get_draft_with_author.return_value = draft_dict

    draft, author_name = await fetch_draft_with_context("507f1f77bcf86cd799439011", 123, draft_service)

    assert draft.id == "507f1f77bcf86cd799439011"
    assert draft.name == "Test Draft"
    assert author_name == "Test User"
    draft_service.get_draft_with_author.assert_called_once_with(draft_id="507f1f77bcf86cd799439011", user_id=123)


@pytest.mark.asyncio
async def test_fetch_draft_with_context_fallback_to_username():
    """Test fetch_draft_with_context uses username when author_name is None."""
    draft_service = AsyncMock()
    draft_dict = {
        "_id": "507f1f77bcf86cd799439011",
        "id": "507f1f77bcf86cd799439011",
        "user_id": 123,
        "name": "Test Draft",
        "status": "draft",
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
        "inputs": {"description": "Test description", "synonyms": [], "attributes_markdown": "## Test\n- test: value"},
        "generated_json": None,
        "action_log": [],
        "author_name": None,
        "author_username": "testuser",
    }
    draft_service.get_draft_with_author.return_value = draft_dict

    draft, author_name = await fetch_draft_with_context("507f1f77bcf86cd799439011", 123, draft_service)

    assert author_name == "testuser"


@pytest.mark.asyncio
async def test_fetch_draft_with_context_not_found():
    """Test fetch_draft_with_context raises 404 when draft not found."""
    draft_service = AsyncMock()
    draft_service.get_draft_with_author.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        await fetch_draft_with_context("507f1f77bcf86cd799439011", 123, draft_service)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Draft not found"


# Tests for check_draft_permissions


def test_check_draft_permissions_owner_can_edit_draft_status():
    """Test owner can edit and delete draft in 'draft' status."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_edit, can_delete = check_draft_permissions(draft, user)

    assert can_edit is True
    assert can_delete is True


def test_check_draft_permissions_owner_can_edit_public_status():
    """Test owner can edit and delete draft in 'public' status."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="public",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_edit, can_delete = check_draft_permissions(draft, user)

    assert can_edit is True
    assert can_delete is True


def test_check_draft_permissions_owner_cannot_edit_submitted():
    """Test owner cannot edit or delete draft in 'submitted' status."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="submitted",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_edit, can_delete = check_draft_permissions(draft, user)

    assert can_edit is False
    assert can_delete is False


def test_check_draft_permissions_non_owner_cannot_edit():
    """Test non-owner cannot edit or delete any draft."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="public",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    user = User(
        id=456,
        login="otheruser",
        name="Other User",
        email="other@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    can_edit, can_delete = check_draft_permissions(draft, user)

    assert can_edit is False
    assert can_delete is False


def test_check_draft_permissions_unauthenticated_cannot_edit():
    """Test unauthenticated user cannot edit or delete any draft."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="public",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )

    can_edit, can_delete = check_draft_permissions(draft, None)

    assert can_edit is False
    assert can_delete is False


def test_check_draft_permissions_private_draft_non_owner_raises_404():
    """Test accessing private draft without ownership raises 404."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    user = User(
        id=456,
        login="otheruser",
        name="Other User",
        email="other@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    with pytest.raises(HTTPException) as exc_info:
        check_draft_permissions(draft, user)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Draft not found"


def test_check_draft_permissions_private_draft_unauthenticated_raises_404():
    """Test accessing private draft when unauthenticated raises 404."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )

    with pytest.raises(HTTPException) as exc_info:
        check_draft_permissions(draft, None)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Draft not found"


# Tests for parse_finding_model_from_draft


def test_parse_finding_model_from_draft_success():
    """Test parse_finding_model_from_draft returns finding model when valid JSON."""
    generated_json = """{
        "oifm_id": "OIFM_TEST_123456",
        "name": "Test Finding",
        "description": "Test description",
        "synonyms": ["test1", "test2"],
        "attributes": [
            {
                "oifma_id": "OIFMA_TEST_789012",
                "name": "presence",
                "description": "Presence of finding",
                "type": "choice",
                "values": [
                    {"value_code": "OIFMA_TEST_789012.0", "name": "absent", "description": "Not visible"},
                    {"value_code": "OIFMA_TEST_789012.1", "name": "present", "description": "Visible"}
                ],
                "required": false,
                "max_selected": 1
            }
        ]
    }"""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json=generated_json,
        action_log=[],
    )

    finding_model = parse_finding_model_from_draft(draft)

    assert finding_model is not None
    assert finding_model.name == "Test Finding"
    assert finding_model.description == "Test description"
    assert len(finding_model.attributes) == 1


def test_parse_finding_model_from_draft_no_json():
    """Test parse_finding_model_from_draft returns None when no generated JSON."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json=None,
        action_log=[],
    )

    finding_model = parse_finding_model_from_draft(draft)

    assert finding_model is None


def test_parse_finding_model_from_draft_invalid_json():
    """Test parse_finding_model_from_draft returns None when invalid JSON."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json='{"invalid": "json", "missing": "required fields"}',
        action_log=[],
    )

    finding_model = parse_finding_model_from_draft(draft)

    assert finding_model is None


# Tests for render_draft_edit_content


def test_render_draft_edit_content():
    """Test render_draft_edit_content returns HTML string."""
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Edit Form</div>"

    result = render_draft_edit_content(request, user, draft, templates)

    assert result == "<div>Edit Form</div>"
    templates.get_template.assert_called_once_with("components/draft_edit_form_content.html")


# Tests for render_draft_preview_content


def test_render_draft_preview_content_basic():
    """Test render_draft_preview_content returns HTML string."""
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="submitted",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Preview Content</div>"

    result = render_draft_preview_content(request, user, draft, None, None, "Test Author", True, True, templates)

    assert result == "<div>Preview Content</div>"
    templates.get_template.assert_called_once_with("components/draft_preview_content.html")


def test_render_draft_preview_content_with_none_user():
    """Test render_draft_preview_content works with None user."""
    request = Mock(spec=Request)
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="public",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        action_log=[],
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Preview Content</div>"

    result = render_draft_preview_content(request, None, draft, None, None, "Test Author", False, False, templates)

    assert result == "<div>Preview Content</div>"


# Tests for build_htmx_response_with_oob


def test_build_htmx_response_with_oob_without_include():
    """Test build_htmx_response_with_oob returns simple response when include_oob=False."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()

    response = build_htmx_response_with_oob(
        "<div>Main Content</div>", draft, "edit", True, False, request, user, templates
    )

    assert response.body == b"<div>Main Content</div>"
    assert response.status_code == 200


def test_build_htmx_response_with_oob_without_generated_json():
    """Test build_htmx_response_with_oob returns simple response when no generated_json."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json=None,
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()

    response = build_htmx_response_with_oob(
        "<div>Main Content</div>", draft, "edit", True, True, request, user, templates
    )

    assert response.body == b"<div>Main Content</div>"


def test_build_htmx_response_with_oob_with_oob_swaps():
    """Test build_htmx_response_with_oob includes OOB swaps when include_oob=True."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Mode Toggle</div>"

    response = build_htmx_response_with_oob(
        "<div>Main Content</div>", draft, "edit", True, True, request, user, templates
    )

    content = response.body.decode("utf-8")
    assert "<div>Main Content</div>" in content
    assert "draft-mode-toggle-header" in content
    assert "hx-swap-oob" in content
    assert "Edit Finding Model Draft" in content


def test_build_htmx_response_with_oob_view_mode_title():
    """Test build_htmx_response_with_oob uses correct title for view mode."""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Mode Toggle</div>"

    response = build_htmx_response_with_oob(
        "<div>Main Content</div>", draft, "view", True, True, request, user, templates
    )

    content = response.body.decode("utf-8")
    assert "Preview Finding Model Draft" in content


# Tests for should_regenerate_model


def test_should_regenerate_model_description_changed():
    """Test should_regenerate_model returns True when description changes."""
    from app.routers.drafts.helpers import should_regenerate_model

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Original description",
            synonyms=["test"],
            attributes_markdown="## Test\n- test: value",
        ),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    new_inputs = FindingModelInputs(
        description="Changed description",
        synonyms=["test"],
        attributes_markdown="## Test\n- test: value",
    )

    result = should_regenerate_model(draft, new_inputs)

    assert result is True


def test_should_regenerate_model_synonyms_changed():
    """Test should_regenerate_model returns True when synonyms change."""
    from app.routers.drafts.helpers import should_regenerate_model

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Test description",
            synonyms=["test1", "test2"],
            attributes_markdown="## Test\n- test: value",
        ),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    new_inputs = FindingModelInputs(
        description="Test description",
        synonyms=["test1", "test2", "test3"],
        attributes_markdown="## Test\n- test: value",
    )

    result = should_regenerate_model(draft, new_inputs)

    assert result is True


def test_should_regenerate_model_attributes_changed():
    """Test should_regenerate_model returns True when attributes change."""
    from app.routers.drafts.helpers import should_regenerate_model

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Test description",
            synonyms=["test"],
            attributes_markdown="## Test\n- test: value",
        ),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    new_inputs = FindingModelInputs(
        description="Test description",
        synonyms=["test"],
        attributes_markdown="## Updated Test\n- test: new value",
    )

    result = should_regenerate_model(draft, new_inputs)

    assert result is True


def test_should_regenerate_model_no_generated_json():
    """Test should_regenerate_model returns True when no generated JSON exists."""
    from app.routers.drafts.helpers import should_regenerate_model

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Test description",
            synonyms=["test"],
            attributes_markdown="## Test\n- test: value",
        ),
        generated_json=None,
        action_log=[],
    )
    new_inputs = FindingModelInputs(
        description="Test description",
        synonyms=["test"],
        attributes_markdown="## Test\n- test: value",
    )

    result = should_regenerate_model(draft, new_inputs)

    assert result is True


def test_should_regenerate_model_no_changes():
    """Test should_regenerate_model returns False when nothing changes."""
    from app.routers.drafts.helpers import should_regenerate_model

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(
            description="Test description",
            synonyms=["test"],
            attributes_markdown="## Test\n- test: value",
        ),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    new_inputs = FindingModelInputs(
        description="Test description",
        synonyms=["test"],
        attributes_markdown="## Test\n- test: value",
    )

    result = should_regenerate_model(draft, new_inputs)

    assert result is False


# Tests for build_update_htmx_response


def test_build_update_htmx_response_basic():
    """Test build_update_htmx_response returns HTMLResponse with correct content."""
    from app.routers.drafts.helpers import build_update_htmx_response

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json=None,
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Preview Content</div>"

    response = build_update_htmx_response(
        request=request,
        draft=draft,
        generated_json=None,
        author_name="Test Author",
        current_user=user,
        was_regenerated=True,
        templates=templates,
    )

    assert response.status_code == 200
    content = response.body.decode("utf-8")
    assert "<div>Preview Content</div>" in content
    assert response.headers["HX-Push-Url"] == "/drafts/test-id?mode=view&created=true"
    assert response.headers["x-model-reused"] == "0"  # was regenerated


def test_build_update_htmx_response_with_oob_swaps():
    """Test build_update_htmx_response includes OOB swaps when generated_json exists."""
    from app.routers.drafts.helpers import build_update_htmx_response

    generated_json = """{
        "oifm_id": "OIFM_TEST_123456",
        "name": "Test Finding",
        "description": "Test description",
        "synonyms": ["test1", "test2"],
        "attributes": [
            {
                "oifma_id": "OIFMA_TEST_789012",
                "name": "presence",
                "description": "Presence of finding",
                "type": "choice",
                "values": [
                    {"value_code": "OIFMA_TEST_789012.0", "name": "absent", "description": "Not visible"},
                    {"value_code": "OIFMA_TEST_789012.1", "name": "present", "description": "Visible"}
                ],
                "required": false,
                "max_selected": 1
            }
        ]
    }"""
    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json=generated_json,
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Mode Toggle</div>"

    response = build_update_htmx_response(
        request=request,
        draft=draft,
        generated_json=generated_json,
        author_name="Test Author",
        current_user=user,
        was_regenerated=False,
        templates=templates,
    )

    content = response.body.decode("utf-8")
    assert "draft-mode-toggle-header" in content
    assert "hx-swap-oob" in content
    assert response.headers["x-model-reused"] == "1"  # was not regenerated


def test_build_update_htmx_response_reused_flag():
    """Test build_update_htmx_response sets correct x-model-reused header."""
    from app.routers.drafts.helpers import build_update_htmx_response

    draft = FindingModelDraft(
        id="test-id",
        user_id=123,
        name="Test Draft",
        status="draft",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        inputs=FindingModelInputs(description="Test", synonyms=[], attributes_markdown="## Test\n- test: value"),
        generated_json='{"test": "json"}',
        action_log=[],
    )
    request = Mock(spec=Request)
    user = User(
        id=123,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="",
        organizations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    templates = Mock()
    templates.get_template.return_value.render.return_value = "<div>Content</div>"

    # Test with was_regenerated=True
    response = build_update_htmx_response(
        request=request,
        draft=draft,
        generated_json='{"test": "json"}',
        author_name="Test Author",
        current_user=user,
        was_regenerated=True,
        templates=templates,
    )
    assert response.headers["x-model-reused"] == "0"

    # Test with was_regenerated=False
    response = build_update_htmx_response(
        request=request,
        draft=draft,
        generated_json='{"test": "json"}',
        author_name="Test Author",
        current_user=user,
        was_regenerated=False,
        templates=templates,
    )
    assert response.headers["x-model-reused"] == "1"
