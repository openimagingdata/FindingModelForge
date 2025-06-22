from datetime import datetime

from pydantic import BaseModel, Field


class UserBase(BaseModel):
    """Base user model."""

    login: str
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None


class UserCreate(UserBase):
    """User creation model."""

    github_id: int


class UserUpdate(BaseModel):
    """User update model."""

    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None


class User(UserBase):
    """User model with database fields."""

    id: int
    github_id: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

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

    user_id: int | None = None
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
