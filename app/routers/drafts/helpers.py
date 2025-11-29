"""Helper functions for draft router endpoints."""

from typing import TYPE_CHECKING, Any

from fastapi import HTTPException, Request, status
from findingmodel import FindingModelFull

from app.dependencies import DraftServiceDep
from app.models import FindingModelDraft, User

if TYPE_CHECKING:
    from fastapi.responses import HTMLResponse


def is_htmx_request(request: Request) -> bool:
    """Check if request is from HTMX.

    Args:
        request: FastAPI Request object

    Returns:
        True if request has HX-Request header set to "true"
    """
    return request.headers.get("HX-Request") == "true"


def get_htmx_context(request: Request) -> dict[str, Any]:
    """Extract HTMX-specific request context.

    Args:
        request: FastAPI Request object

    Returns:
        Dictionary with HTMX context:
        - is_htmx: bool - Whether request is from HTMX
        - current_url: str - Current URL from HX-Current-URL header
        - from_public: bool - Whether request came from public drafts page
    """
    return {
        "is_htmx": is_htmx_request(request),
        "current_url": request.headers.get("HX-Current-URL", ""),
        "from_public": request.query_params.get("from") == "public",
    }


async def fetch_draft_with_context(
    draft_id: str,
    user_id: int | None,
    draft_service: DraftServiceDep,
) -> tuple[FindingModelDraft, str]:
    """Fetch draft with author info, raising 404 if not found.

    Args:
        draft_id: Draft ID to fetch
        user_id: Current user ID (None if not authenticated)
        draft_service: Draft service dependency

    Returns:
        Tuple of (draft, author_name)

    Raises:
        HTTPException: 404 if draft not found
    """
    draft_dict = await draft_service.get_draft_with_author(draft_id=draft_id, user_id=user_id)
    if draft_dict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    author_name = draft_dict.get("author_name") or draft_dict.get("author_username", "Unknown")
    draft = FindingModelDraft.model_validate(draft_dict)
    return draft, author_name


def check_draft_permissions(
    draft: FindingModelDraft,
    current_user: User | None,
) -> tuple[bool, bool]:
    """Check edit and delete permissions for a draft.

    Args:
        draft: Draft to check permissions for
        current_user: Current user (None if not authenticated)

    Returns:
        Tuple of (can_edit, can_delete)

    Raises:
        HTTPException: 404 if trying to access private draft without ownership
    """
    # Private drafts require authentication and ownership
    if draft.status == "draft" and (not current_user or draft.user_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    can_edit = current_user is not None and draft.status in ["draft", "public"] and draft.user_id == current_user.id
    can_delete = current_user is not None and draft.status in ["draft", "public"] and draft.user_id == current_user.id
    return can_edit, can_delete


def parse_finding_model_from_draft(draft: FindingModelDraft) -> FindingModelFull | None:
    """Parse finding model from draft's generated JSON.

    Args:
        draft: Draft containing generated_json

    Returns:
        Parsed FindingModelFull or None if parsing fails/no JSON
    """
    if not draft.generated_json:
        return None

    try:
        return FindingModelFull.model_validate_json(draft.generated_json)
    except Exception:
        return None


def render_draft_edit_content(
    request: Request,
    user: User | None,
    draft: FindingModelDraft,
    templates: Any,
) -> str:
    """Render draft edit form content.

    Args:
        request: FastAPI Request object
        user: Current authenticated user (None if not authenticated)
        draft: Draft to render for editing
        templates: Jinja2 templates instance

    Returns:
        Rendered HTML content as string
    """
    return str(
        templates.get_template("components/draft_edit_form_content.html").render(
            request=request,
            user=user,
            draft=draft,
        )
    )


def render_draft_preview_content(
    request: Request,
    user: User | None,
    draft: FindingModelDraft,
    finding_model: FindingModelFull | None,
    thread: Any,
    author_name: str,
    can_edit: bool,
    can_delete: bool,
    templates: Any,
    show_success_message: bool = False,
) -> str:
    """Render draft preview content.

    Args:
        request: FastAPI Request object
        user: Current user (None if not authenticated)
        draft: Draft to preview
        finding_model: Parsed finding model (None if not available)
        thread: Comment thread for the draft
        author_name: Name of draft author
        can_edit: Whether current user can edit this draft
        can_delete: Whether current user can delete this draft
        templates: Jinja2 templates instance
        show_success_message: Whether to show success alert (default: False)

    Returns:
        Rendered HTML content as string
    """
    return str(
        templates.get_template("components/draft_preview_content.html").render(
            request=request,
            user=user,
            draft=draft,
            finding_model=finding_model,
            thread=thread,
            reference_type="draft",
            reference_id=str(draft.id),
            current_user=user,
            show_ids=bool(draft.status == "submitted"),
            show_json=bool(draft.status == "submitted"),
            author_name=author_name,
            can_edit=can_edit,
            can_delete=can_delete,
            show_success_message=show_success_message,
        )
    )


def build_htmx_response_with_oob(
    main_content: str,
    draft: FindingModelDraft,
    mode: str,
    can_edit: bool,
    include_oob: bool,
    request: Request,
    user: User | None,
    templates: Any,
) -> "HTMLResponse":
    """Build HTMX response with optional OOB swaps for mode toggle and title.

    Args:
        main_content: Main HTML content to return
        draft: Draft being displayed
        mode: Current mode ("view" or "edit")
        can_edit: Whether user can edit the draft
        include_oob: Whether to include OOB swaps
        request: FastAPI Request object
        user: Current user (None if not authenticated)
        templates: Jinja2 templates instance

    Returns:
        HTMLResponse with main content and OOB swaps if requested
    """
    from fastapi.responses import HTMLResponse

    if not include_oob or not draft.generated_json:
        return HTMLResponse(content=main_content)

    # Build mode toggle header OOB swap
    target_container = "#main-content"
    mode_toggle_header = str(
        templates.get_template("components/draft_mode_toggle_header.html").render(
            request=request,
            user=user,
            draft=draft,
            mode=mode,
            can_edit=can_edit,
            target_container=target_container,
        )
    )

    # Create OOB swap for page title
    page_title_text = "Edit Finding Model Draft" if mode == "edit" else "Preview Finding Model Draft"
    title_oob = (
        f'<h1 id="page-title" class="text-3xl font-bold text-gray-900 dark:text-white mb-2" '
        f'hx-swap-oob="true">{page_title_text}</h1>'
    )

    # Combine main content with OOB swaps
    combined_content = f"""{main_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>
{title_oob}"""

    return HTMLResponse(content=combined_content)


def build_update_htmx_response(
    request: Request,
    draft: FindingModelDraft,
    generated_json: str | None,
    author_name: str,
    current_user: User,
    was_regenerated: bool,
    templates: Any,
) -> "HTMLResponse":
    """Build HTMX response after draft update.

    Args:
        request: FastAPI Request object
        draft: Updated draft
        generated_json: Generated finding model JSON
        author_name: Name of draft author
        current_user: Current user
        was_regenerated: Whether model was regenerated
        templates: Jinja2 templates instance

    Returns:
        HTMLResponse with draft preview and OOB swaps
    """
    from fastapi.responses import HTMLResponse

    # Parse the generated finding model
    finding_model: FindingModelFull | None = None
    if generated_json:
        try:
            finding_model = FindingModelFull.model_validate_json(generated_json)
        except Exception:
            finding_model = None

    # Set headers including reuse indicator and URL push
    response_headers = {
        "HX-Push-Url": f"/drafts/{draft.id}?mode=view&created=true",
        "x-model-reused": "0" if was_regenerated else "1",
    }

    # Render the main draft preview content
    draft_content = render_draft_preview_content(
        request=request,
        user=current_user,
        draft=draft,
        finding_model=finding_model,
        thread=None,  # No comment thread in update context
        author_name=author_name,
        can_edit=draft.status in ["draft", "public"],
        can_delete=draft.status in ["draft", "public"] and draft.user_id == current_user.id,
        templates=templates,
        show_success_message=True,  # Show success alert after update
    )

    # Include mode toggle header OOB swap if the draft now has generated JSON
    if draft.generated_json:
        # Use unified container across all workflows
        target_container = "#main-content"

        # Include mode toggle header OOB swap
        mode_toggle_header = str(
            templates.get_template("components/draft_mode_toggle_header.html").render(
                request=request,
                user=current_user,
                draft=draft,
                mode="view",  # We're transitioning to view mode
                can_edit=draft.status in ["draft", "public"],
                target_container=target_container,
            )
        )

        # Combine main content with OOB swap for mode toggle header
        combined_content = f"""{draft_content}
<div id="draft-mode-toggle-header" hx-swap-oob="true">
{mode_toggle_header}
</div>"""

        return HTMLResponse(
            content=combined_content,
            headers=response_headers,
        )
    else:
        return HTMLResponse(
            content=draft_content,
            headers=response_headers,
        )
