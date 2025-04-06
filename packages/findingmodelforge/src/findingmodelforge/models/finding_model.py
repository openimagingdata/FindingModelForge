from enum import Enum
from typing import Annotated, Literal, Sequence

from jinja2 import Template
from pydantic import BaseModel, Field


class AttributeType(str, Enum):
    CHOICE = "choice"
    NUMERIC = "numeric"


# Define a ID length constant
ID_LENGTH = 6

AttributeId = Annotated[
    str,
    Field(
        description="The ID of the attribute in the Open Imaging Data Model Finding Model registry",
        pattern=r"^OIFMA_[A-Z]{3,4}_[0-9]{" + str(ID_LENGTH) + r"}$",
    ),
]


class ChoiceValue(BaseModel):
    """A value that a radiologist might choose for a choice attribute. For example, the severity of a finding might be
    severe, or the shape of a finding might be oval."""

    name: str
    description: str | None = None


AttributeNameStr = Annotated[
    str,
    Field(
        description="Short, descriptive name of the attribute as an case-sensitive English phrase (preserving capitalization of acronyms).",  # noqa: E501
        min_length=3,
        max_length=100,
    ),
]

AttributeDescriptionStr = Annotated[
    str | None,
    Field(
        default=None,
        description="A one-to-two sentence description of the attribute that might be included in a medical textbook",
        min_length=5,
        max_length=500,
    ),
]

RequiredBool = Annotated[
    bool,
    Field(
        default=False,
        description="Whether the attribute is used every time a radiologist describes the finding",
    ),
]

MaxSelectedInt = Annotated[
    int | None,
    Field(
        default=None,
        description="The maximum number of values that can be selected for a choice attribute (defaults to 1).",
        ge=1,
    ),
]


class ChoiceAttribute(BaseModel):
    """An attribute of a radiology finding where the radiologist would choose from a list of options. For example,
    the severity of a finding (mild, moderate, or severe), or the shape of a finding (round, oval, or
    irregular). For attributes which can have multiple values from a series of choices, max_selected can be set to"
    a value greater than 1 or "all"."""

    name: AttributeNameStr
    description: AttributeDescriptionStr = None
    type: Literal[AttributeType.CHOICE] = AttributeType.CHOICE
    values: Annotated[list[ChoiceValue], Field(..., min_length=2)]
    required: RequiredBool = False
    max_selected: MaxSelectedInt = None


class ChoiceAttributeIded(BaseModel):
    oifma_id: AttributeId
    name: AttributeNameStr
    description: AttributeDescriptionStr = None
    type: Literal[AttributeType.CHOICE] = AttributeType.CHOICE
    values: Annotated[list[ChoiceValue], Field(..., min_length=2)]
    required: RequiredBool = False
    max_selected: MaxSelectedInt = None


ChoiceAttributeIded.__doc__ = ChoiceAttribute.__doc__

MinimumNumeric = Annotated[
    int | float | None,
    Field(
        default=None,
        description="The minimum value for the attribute.",
    ),
]

MaximumNumeric = Annotated[
    int | float | None,
    Field(
        default=None,
        description="The maximum value for the attribute.",
    ),
]

UnitStr = Annotated[
    str | None,
    Field(
        default=None,
        description="The unit of measure for the attribute",
    ),
]


class NumericAttribute(BaseModel):
    """An attribute of a radiology finding where the radiologist would choose a number from a range. For example, the
    size of a finding might be up to 10 cm or the number of findings might be between 1 and 10."""

    name: AttributeNameStr
    description: AttributeDescriptionStr = None
    type: Literal[AttributeType.NUMERIC] = AttributeType.NUMERIC
    minimum: MinimumNumeric = None
    maximum: MaximumNumeric = None
    unit: UnitStr = None
    required: RequiredBool = False


class NumericAttributeIded(BaseModel):
    oifma_id: AttributeId
    name: AttributeNameStr
    description: AttributeDescriptionStr = None
    type: Literal[AttributeType.NUMERIC] = AttributeType.NUMERIC
    minimum: MinimumNumeric = None
    maximum: MaximumNumeric = None
    unit: UnitStr = None
    required: RequiredBool = False


NumericAttributeIded.__doc__ = NumericAttribute.__doc__

ATTRIBUTE_FIELD_DESCRIPTION = (
    "An attribute that a radiologist would use to characterize a particular finding in a radiology report"
)
Attribute = Annotated[
    ChoiceAttribute | NumericAttribute,
    Field(
        discriminator="type",
        description=ATTRIBUTE_FIELD_DESCRIPTION,
    ),
]

AttributeIded = Annotated[
    ChoiceAttributeIded | NumericAttributeIded,
    Field(discriminator="type", description=ATTRIBUTE_FIELD_DESCRIPTION),
]
# The template for the markdown representation of the finding model

BASE_MARKDOWN_TEMPLATE_TEXT = """
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
{% if attribute_type.max_selected and attribute.max_selected > 1 %}
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

BASE_MARKDOWN_TEMPLATE = Template(BASE_MARKDOWN_TEMPLATE_TEXT)

NameString = Annotated[
    str,
    Field(
        description="The name of the finding model. This should be a short, descriptive name that is easy to remember",
        min_length=5,
    ),
]

DescriptionString = Annotated[
    str,
    Field(
        description="A one-to-two sentence description of the finding that might be included in a textbook",
        min_length=5,
    ),
]

SynonymSequence = Annotated[
    Sequence[str] | None,
    Field(
        default=None,
        description="Other terms that might be used to describe the finding in a radiology report",
        min_length=1,
    ),
]

TagSequence = Annotated[
    Sequence[str] | None,
    Field(
        default=None,
        description="Tags that might be used to categorize the finding among other findings",
        min_length=1,
    ),
]

ATTRIBUTES_FIELD_DESCRIPTION = (
    "The attributes a radiologist would use to characterize a particular finding in a radiology report"
)


class FindingModelBase(BaseModel):
    """The definition of a radiology finding what the finding is such as might be included in a textbook
    along with definitions of the relevant attributes that a radiologist might use to characterize the finding in a
    radiology report."""

    name: NameString
    description: DescriptionString
    synonyms: SynonymSequence = None
    tags: TagSequence = None
    attributes: Annotated[
        Sequence[Attribute],
        Field(min_length=1, description=ATTRIBUTES_FIELD_DESCRIPTION),
    ]

    def as_markdown(self) -> str:
        return BASE_MARKDOWN_TEMPLATE.render(
            name=self.name,
            synonyms=self.synonyms,
            tags=self.tags,
            description=self.description,
            attributes=self.attributes,
        )


OifmIdStr = Annotated[
    str,
    Field(
        description="The ID of the finding model in the Open Imaging Data Model Finding Model registry",
        pattern=r"^OIFM_[A-Z]{3,4}_[0-9]{" + str(ID_LENGTH) + r"}$",
    ),
]

FULL_MARKDOWN_TEMPLATE_TEXT = """
# {{ name }} 

*{{ oifm_id }}*

{% if synonyms %}
**Synonyms:** {{ synonyms | join(", ") }}
{% endif %}

{% if tags %}
**Tags:** {{ tags | join(", ") }}
{% endif %}

{% if description %}
{{ description }}
{% endif %}


## Attributes

{% for attribute in attributes %}
### {{ attribute.name }}
*{{ attribute.oifma_id }}*

{% if attribute.description %}
{{ attribute.description }}  
{% endif %}

{% if attribute.type == "choice" %}
{% if attribute.max_selected and attribute.max_selected > 1 %}
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

FULL_MARKDOWN_TEMPLATE = Template(FULL_MARKDOWN_TEMPLATE_TEXT)


class FindingModelFull(BaseModel):
    oifm_id: OifmIdStr
    name: NameString
    description: DescriptionString
    synonyms: SynonymSequence = None
    tags: TagSequence = None
    attributes: Annotated[
        Sequence[AttributeIded],
        Field(min_length=1, description=ATTRIBUTES_FIELD_DESCRIPTION),
    ]

    def as_markdown(self) -> str:
        return FULL_MARKDOWN_TEMPLATE.render(
            oifm_id=self.oifm_id,
            name=self.name,
            synonyms=self.synonyms,
            tags=self.tags,
            description=self.description,
            attributes=self.attributes,
        )


FindingModelFull.__doc__ = FindingModelBase.__doc__
