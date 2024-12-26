from pydantic import BaseModel, Field


class BaseFindingInfo(BaseModel):
    """
    Base class for finding information, with simple name and description ± synonyms
    """

    name: str = Field(..., title="Finding Name", description="The name of the finding")
    synonyms: list[str] | None = Field(
        default=None,
        title="Synonyms",
        description="Synonyms for the finding name, especially those used by radiologists, including acronyms",
    )
    description: str = Field(..., title="Description", description="The description of the finding")


class DetailedFindingInfo(BaseFindingInfo):
    """
    Detailed class for finding information, with a detailed description and citations.
    """

    detail: str | None = Field(default=None, title="Detail", description="A detailed description of the finding")
    citations: list[str] | None = Field(
        default=None, title="Citations", description="Citations (ideally URLs) for the detailed description"
    )
