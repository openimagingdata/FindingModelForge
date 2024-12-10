from pathlib import Path

from findingmodelforge import settings
from findingmodelforge.models.finding_info import BaseFindingInfo
from findingmodelforge.models.finding_model import FindingModelBase

from .clients import get_async_instructor_client
from .prompt_template import create_prompt_messages, load_prompt_template


async def create_finding_model_from_markdown(
    finding_info: BaseFindingInfo,
    /,
    markdown_path: str | Path | None = None,
    markdown_text: str | None = None,
    openai_model: str = settings.openai_default_model,
) -> FindingModelBase:
    if not markdown_path and not markdown_text:
        raise ValueError("Either markdown_path or markdown_text must be provided")
    if markdown_path and markdown_text:
        raise ValueError("Only one of markdown_path or markdown_text should be provided")
    if markdown_path:
        markdown_path = Path(markdown_path)
        if not markdown_path.exists():
            raise FileNotFoundError(f"Markdown file not found: {markdown_path}")
        markdown_text = markdown_path.read_text()
    prompt_template = load_prompt_template("get_finding_model_from_outline")
    messages = create_prompt_messages(
        prompt_template,
        finding_info=finding_info,
        outline=markdown_text,
    )
    client = get_async_instructor_client()
    result = await client.chat.completions.create(
        messages=messages,
        response_model=FindingModelBase,
        model=openai_model,
    )
    if not isinstance(result, FindingModelBase):
        raise ValueError("Finding model not returned.")
    return result


STANDARD_CODES = [
    {"name": "presence", "snomed_code": "705057003", "snomed_display": "Presence (property) (qualifier value)"},
    {
        "name": "absent",
        "radlex_code": "RID28473",
        "radlex_display": "absent",
        "snomed_code": "2667000",
        "snomed_display": "Absent (qualifier value)",
    },
    {
        "name": "present",
        "radlex_code": "RID28472",
        "radlex_display": "present",
        "snomed_code": "52101004",
        "snomed_display": "Present (qualifier value)",
    },
    {
        "name": "indeterminate",
        "radlex_code": "RID39110",
        "radlex_display": "indeterminate",
        "snomed_code": "82334004",
        "snomed_display": "Indeterminate (qualifier value)",
    },
    {
        "name": "unknown",
        "radlex_code": "RID5655",
        "radlex_display": "unknown",
        "snomed_code": "261665006",
        "snomed_display": "Unknown (qualifier value)",
    },
    {
        "name": "location",
        "radlex_code": "RID39038",
        "radlex_display": "location",
        "snomed_code": "758637006",
        "snomed_display": "Anatomic location (property) (qualifier value)",
    },
    {"name": "size", "snomed_code": "246115007", "snomed_display": "Size (attribute)"},
    {"name": "changed", "snomed_code": "263703002", "snomed_display": "Changed status (qualifier value)"},
    {
        "name": "stable",
        "radlex_code": "RID5734",
        "radlex_display": "stable",
        "snomed_code": "58158008",
        "snomed_display": "Stable (qualifier value)",
    },
    {
        "name": "unchanged",
        "radlex_code": "RID39268",
        "radlex_display": "unchanged",
        "snomed_code": "260388006",
        "snomed_display": "No status change (qualifier value)",
    },
    {
        "name": "increased",
        "radlex_code": "RID36043",
        "radlex_display": "increased",
        "snomed_code": "35105006",
        "snomed_display": "Increased (qualifier value)",
    },
    {
        "name": "decreased",
        "radlex_code": "RID36044",
        "radlex_display": "decreased",
        "snomed_code": "1250004",
        "snomed_display": "Decreased (qualifier value)",
    },
    {
        "name": "new",
        "radlex_code": "RID5720",
        "radlex_display": "new",
        "snomed_code": "7147002",
        "snomed_display": "New (qualifier value)",
    },
    {
        "name": "quantity",
        "radlex_code": "RID5761",
        "radlex_display": "quantity descriptor",
        "snomed_code": "246205007",
        "snomed_display": "Quantity (attribute)",
    },
    {
        "name": "multiple",
        "radlex_code": "RID5765",
        "radlex_display": "multiple",
        "snomed_code": "255204007",
        "snomed_display": "Multiple (qualifier value)",
    },
    {
        "name": "single",
        "radlex_code": "RID5762",
        "radlex_display": "single",
        "snomed_code": "50607009",
        "snomed_display": "Singular (qualifier value)",
    },
    {"name": "severity", "snomed_code": "246112005", "snomed_display": "Severity (attribute)"},
    {
        "name": "mild",
        "radlex_code": "RID5671",
        "radlex_display": "mild",
        "snomed_code": "255604002",
        "snomed_display": "Mild (qualifier value)",
    },
    {
        "name": "moderate",
        "radlex_code": "RID5672",
        "radlex_display": "moderate",
        "snomed_code": "1255665007",
        "snomed_display": "Moderate (qualifier value)",
    },
    {
        "name": "severe",
        "radlex_code": "RID5673",
        "radlex_display": "severe",
        "snomed_code": "24484000",
        "snomed_display": "Severe (severity modifier) (qualifier value)",
    },
    {
        "name": "change",
        "radlex_code": "RID49896",
        "radlex_display": "change",
        "snomed_code": "243326001",
        "snomed_display": "Changing (qualifier value)",
    },
    {
        "name": "location",
        "radlex_code": "RID39038",
        "radlex_display": "location",
        "snomed_code": "758637006",
        "snomed_display": "Anatomic location (property) (qualifier value)",
    },
]
