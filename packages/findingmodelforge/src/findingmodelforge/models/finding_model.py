from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class AttributeType(str, Enum):
    CHOICE = "choice"
    NUMERIC = "numeric"


class ChoiceValue(BaseModel):
    """A value that a radiologist might choose for a choice attribute. For example, the severity of a finding might be
    severe, or the shape of a finding might be oval."""

    name: str
    description: str | None = None


class ChoiceAttribute(BaseModel):
    """An attribute of a radiology finding where the radiologist would choose from a list of options. For example,
    the severity of a finding might be mild, moderate, or severe, or the shape of a finding might be round, oval, or
    irregular."""

    name: str
    description: str | None = None
    type: Literal[AttributeType.CHOICE] = AttributeType.CHOICE
    values: Annotated[list[ChoiceValue], Field(..., min_length=2)]
    required: bool = Field(
        False, description="Whether the attribute is used every time a radiologist describes the finding"
    )


class NumericAttribute(BaseModel):
    """An attribute of a radiology finding where the radiologist would choose a number from a range. For example, the
    size of a finding might be up to 10 cm or the number of findings might be between 1 and 10."""

    name: str
    description: str | None = None
    type: Literal[AttributeType.NUMERIC] = AttributeType.NUMERIC
    minimum: int | float | None = None
    maximum: int | float | None = None
    unit: str | None = Field(None, description="The unit of measure for the attribute")
    required: bool = Field(
        False, description="Whether the attribute is used every time a radiologist describes the finding"
    )


Attribute = Annotated[
    ChoiceAttribute | NumericAttribute,
    Field(
        discriminator="type",
        description="An attribute that a radiologist would use to characterize a particular finding in a radiology report",  # noqa: E501
    ),
]


class FindingModelBase(BaseModel):
    """The definition of a radiology finding what the finding is such as might be included in a textbook
    along with definitions of the relevant attributes that a radiologist might use to characterize the finding in a
    radiology report."""

    finding_name: str = Field(..., title="Finding Name", description="The name of a raidology finding")
    description: str = Field(
        ...,
        title="Description",
        description="A one-to-two sentence description of the finding that might be included in a textbook",
    )
    attributes: Annotated[
        list[Attribute],
        Field(
            ...,
            min_length=1,
            title="Attributes",
            description="The attributes a radiologist would use to characterize a particular finding in a radiology report",  # noqa: E501
        ),
    ]
    contains_expert_input: bool = Field(
        default=False,
        title="Contains Expert Input",
        description="Whether the finding model contains expert input",
        exclude=True,
    )
    fragment_basis: int = Field(
        default=0,
        title="Fragment Basis",
        description="The number of fragments used to generate and updating the finding model",
        exclude=True,
    )

    def model_dump_extra(self):
        return {
            **self.model_dump(),
            **{
                "contains_expert_input": self.contains_expert_input,
                "fragment_basis": self.fragment_basis,
            },
        }
