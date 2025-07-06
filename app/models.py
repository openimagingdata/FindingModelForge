from datetime import datetime

from pydantic import BaseModel, Field


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


class Organization(BaseModel):
    """Organization model."""

    code: str = Field(min_length=3, max_length=4, pattern=r"^[A-Z]+$")  # 3-4 uppercase letters
    name: str
    url: str | None = None


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


# Finding Model Creation Models


class FindingNameCheck(BaseModel):
    """Request to check if a finding name exists."""

    name: str = Field(min_length=2, max_length=200)


class FindingInfoRequest(BaseModel):
    """Request to create finding information from just a name."""

    name: str = Field(min_length=2, max_length=200)


class FindingInfoEditRequest(BaseModel):
    """Request for the user to edit finding information before proceeding."""

    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    synonyms: list[str] | None = Field(default=None, max_length=20)


class SimilarModelsRequest(BaseModel):
    """Request to find similar models."""

    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    synonyms: list[str] | None = Field(default=None, max_length=20)


class NameAvailabilityResponse(BaseModel):
    """Response for name availability check."""

    available: bool
    message: str = ""


class IndexEntryResponse(BaseModel):
    """Response containing index entry information."""

    oifm_id: str
    name: str
    filename: str
    description: str | None = None
    synonyms: list[str] | None = None
    tags: list[str] | None = None


class FindingInfoResponse(BaseModel):
    """Response containing basic finding information."""

    name: str
    description: str
    synonyms: list[str] | None = None


class SimilarModelResponse(BaseModel):
    """Response containing similar model information."""

    oifm_id: str
    name: str
    description: str | None = None
    synonyms: list[str] | None = None


class SimilarModelsAnalysis(BaseModel):
    """Analysis of similar models."""

    similar_models: list[SimilarModelResponse]
    recommendation: str  # "edit_existing" or "create_new"
    confidence: float


class FindingModelRequest(BaseModel):
    """Request to create a full finding model."""

    finding_name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    synonyms: list[str] | None = Field(default=None, max_length=20)
    tags: list[str] | None = Field(default=None, max_length=20)
    attributes_markdown: str = Field(min_length=10, max_length=10000)


class GenerateModelRequest(BaseModel):
    """Request to generate the final finding model from FindingInfo and attributes markdown."""

    name: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=10, max_length=2000)
    synonyms: list[str] | None = Field(default=None, max_length=20)
    attributes_markdown: str = Field(min_length=10, max_length=10000)


class FindingModelCreationStep(BaseModel):
    """Represents the current step in finding model creation."""

    step: int
    step_name: str
    completed: bool = False
    data: dict[str, str] = Field(default_factory=dict)
