from enum import Enum
from typing import Annotated, Literal, Sequence

from jinja2 import Template
from pydantic import BaseModel, Field, model_validator


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
    the severity of a finding (mild, moderate, or severe), or the shape of a finding (round, oval, or
    irregular). For attributes which can have multiple values from a series of choices, max_selected can be set to"
    a value greater than 1 or "all"."""

    name: str
    description: str | None = None
    type: Literal[AttributeType.CHOICE] = AttributeType.CHOICE
    values: Annotated[list[ChoiceValue], Field(..., min_length=2)]
    required: bool = Field(
        default=False, description="Whether the attribute is used every time a radiologist describes the finding"
    )

    # Make a after-validator to check that if max_select is set to a value greater than the length of
    # the number of choices, max_selected just gets set to the number of choices.
    @model_validator(mode="after")
    def check_max_selected(self):
        if self.max_selected > len(self.values):
            self.max_selected = len(self.values)
        return self

    max_selected: int = Field(
        default=1, description="The maximum number of values that can be selected for the attribute"
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
        default=False, description="Whether the attribute is used every time a radiologist describes the finding"
    )


Attribute = Annotated[
    ChoiceAttribute | NumericAttribute,
    Field(
        discriminator="type",
        description="An attribute that a radiologist would use to characterize a particular finding in a radiology report",  # noqa: E501
    ),
]

MARKDOWN_TEMPLATE_TEXT = """
# {{ name }}

{% if synonyms %}
**Synonyms:** {{ synonyms | join(", ") }}
{% endif %}

{% if tags %}
**Tags:** {{ tags | join(", ") }}
{% endif %}

{{ description }}

## Attributes

{% for attribute in attributes %}
### {{ attribute.name }}

{{ attribute.description }}  


{% if attribute.type == "choice" %}
{% if attribute.max_selected > 1 %}
*Select up to {{ attribute.max_selected }}:*
{% else %}
*Select one:*
{% endif %}

{% for value in attribute.values %}
- **{{ value.name }}**: {{ value.description }}
{% endfor %}

{% elif attribute.type == "numeric" %}
{% if attribute.minimum %}
Mininum: {{ attribute.minimum }}
{% endif %}
{% if attribute.maximum %}
Maximum: {{ attribute.maximum }}
{% endif %}
{% if attribute.unit %}
Unit: {{ attribute.unit }}
{% endif %}
{% endif %}
{% endfor %}
"""

MARKDOWN_TEMPLATE = Template(MARKDOWN_TEMPLATE_TEXT)


class FindingModelBase(BaseModel):
    """The definition of a radiology finding what the finding is such as might be included in a textbook
    along with definitions of the relevant attributes that a radiologist might use to characterize the finding in a
    radiology report."""

    name: str = Field(..., title="Finding Name", description="The name of a raidology finding")
    description: str = Field(
        ...,
        title="Description",
        description="A one-to-two sentence description of the finding that might be included in a textbook",
    )
    synonyms: Sequence[str] | None = Field(
        default=None,
        title="Synonyms",
        description="Other terms that might be used to describe the finding in a radiology report",
    )
    tags: Sequence[str] | None = Field(
        default=None,
        title="Tags",
        description="Tags that might be used to categorize the finding among other findings",
    )
    attributes: Annotated[
        Sequence[Attribute],
        Field(
            ...,
            min_length=1,
            title="Attributes",
            description="The attributes a radiologist would use to characterize a particular finding.",
        ),
    ]

    def as_markdown(self) -> str:
        return MARKDOWN_TEMPLATE.render(
            name=self.name,
            synonyms=self.synonyms,
            tags=self.tags,
            description=self.description,
            attributes=self.attributes,
        )
