from datetime import datetime
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user model."""

    login: str  # GitHub username
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    organizations: list[str] | None = None


class UserCreate(UserBase):
    """User creation model."""

    id: int  # GitHub ID becomes the primary ID


class UserUpdate(BaseModel):
    """User update model."""

    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    organizations: list[str] | None = None


class User(UserBase):
    """User model with database fields."""

    id: int  # GitHub ID as primary key
    is_active: bool = True
    created_at: datetime
    updated_at: datetime
    comment_index: list["UserCommentEntry"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class GitHubUser(BaseModel):
    """GitHub user data from OAuth."""

    id: int
    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    type: str
    site_admin: bool = False


class Token(BaseModel):
    """JWT token response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token payload data."""

    user_id: int | None = None  # GitHub ID
    username: str | None = None


class GitHubTokenResponse(BaseModel):
    """GitHub OAuth token response."""

    access_token: str
    token_type: str = "bearer"
    scope: str | None = None


class HealthCheck(BaseModel):
    """Health check response."""

    status: str = "healthy"
    timestamp: datetime = Field(default_factory=datetime.now)
    version: str
    environment: str


# Comment System Models


class UserCommentEntry(BaseModel):
    """User comment entry for rate limiting and user comment index."""

    reference_type: Literal["finding_model", "draft"]
    reference_id: str  # oifm_id for models, draft ObjectId for drafts
    finding_name: str  # Human-readable name for display
    comment_id: str  # Comment ID for direct access
    created_at: datetime


class Comment(BaseModel):
    """Individual comment with optional nested replies."""

    id: str = Field(default_factory=lambda: str(uuid4()))  # Unique ID for references
    user_id: int  # GitHub user ID
    user_name: str  # Cached for display
    user_avatar_url: str | None = None
    content: str = Field(min_length=1, max_length=2000)
    created_at: datetime
    replies: list["Comment"] = Field(default_factory=list)  # Single-level only
    reported: bool = False
    reported_by: int | None = None  # User ID who reported
    reported_at: datetime | None = None


class CommentThread(BaseModel):
    """Comment thread for a specific finding model or draft."""

    id: str  # MongoDB ObjectId
    reference_type: Literal["finding_model", "draft"]
    reference_id: str  # oifm_id for models, draft ObjectId for drafts
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0
    reported_count: int = 0
    comments: list[Comment] = Field(default_factory=list)


# Finding Model Creation Models


class IndexEntryResponse(BaseModel):
    """Response containing index entry information."""

    oifm_id: str
    name: str
    filename: str
    description: str | None = None
    synonyms: list[str] | None = None
    tags: list[str] | None = None


class FindingModelRequest(BaseModel):
    """Request to create a full finding model."""

    finding_name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    synonyms: list[str] | None = Field(default=None, max_length=20)
    tags: list[str] | None = Field(default=None, max_length=20)
    attributes_markdown: str = Field(min_length=10, max_length=10000)


class FindingModelCreationStep(BaseModel):
    """Represents the current step in finding model creation."""

    step: int
    step_name: str
    completed: bool = False
    data: dict[str, str] = Field(default_factory=dict)


# Removed unused step form models - now using Form() parameters directly in routes


# ===== Draft workflow models =====


class DraftStatus(str, Enum):
    """Status values for finding model drafts."""

    DRAFT = "draft"
    PUBLIC = "public"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under-review"
    ADDED = "added"
    DECLINED = "declined"


class FindingModelInputs(BaseModel):
    """User-provided inputs for a finding model draft (excluding name)."""

    description: str
    synonyms: list[str] | None = None
    attributes_markdown: str | None = None


class LogEntry(BaseModel):
    """Audit entry for draft actions."""

    timestamp: datetime
    user_id: int
    action: str
    details: dict[str, Any] | None = None


class FindingModelDraft(BaseModel):
    """Draft representation persisted in MongoDB."""

    id: str
    user_id: int
    author_username: str | None = None
    author_name: str | None = None
    name: str
    created_at: datetime
    updated_at: datetime
    inputs: FindingModelInputs
    generated_json: str | None = None
    status: DraftStatus = DraftStatus.DRAFT
    action_log: list[LogEntry] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SuggestionCreate(BaseModel):
    """Create suggestion model for form input validation."""

    content: str = Field(..., min_length=1, max_length=300)
    submitter_email: EmailStr | None = None


class Suggestion(BaseModel):
    """Suggestion model for storing user feedback."""

    id: str = Field(alias="_id")
    content: str
    user_id: int | None = None
    submitter_email: EmailStr | None = None
    created_at: datetime

    model_config = ConfigDict(populate_by_name=True)
