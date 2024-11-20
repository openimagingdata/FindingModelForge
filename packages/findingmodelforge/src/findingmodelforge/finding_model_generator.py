from typing import Any

from pydantic import BaseModel, Field

from .clients import get_async_instructor_client, get_async_perplexity_client
from .prompt_template import create_prompt_messages, load_prompt_template

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
DEFAULT_PERPLEXITY_MODEL = "llama-3.1-sonar-large-128k-online"


class DescribedFinding(BaseModel):
    finding_name: str = Field(..., title="Finding Name", description="The name of the finding")
    synonyms: list[str] | None = Field(
        None,
        title="Synonyms",
        description="Synonyms for the finding name, especially those used by radiologists, including acronyms",
    )
    description: str = Field(..., title="Description", description="The description of the finding")


class DescribedFindingWithDetail(DescribedFinding):
    detail: str = Field(..., title="Detail", description="A detailed description of the finding")
    citations: list[str] | None = Field(
        default=None, title="Citations", description="Citations (ideally URLs) for the detailed description"
    )


async def describe_finding_name(finding_name: str, model_name: str = DEFAULT_OPENAI_MODEL) -> DescribedFinding | Any:
    client = get_async_instructor_client()
    prompt_template = load_prompt_template("get_finding_description")
    messages = create_prompt_messages(prompt_template, finding_name=finding_name)
    result = await client.chat.completions.create(
        messages=messages,
        model=model_name,
        response_model=DescribedFinding,
    )
    return result


async def get_detail_on_finding(
    finding: DescribedFinding, model_name: str = DEFAULT_PERPLEXITY_MODEL
) -> DescribedFindingWithDetail | None:
    client = get_async_perplexity_client()
    prompt_template = load_prompt_template("get_finding_detail")
    prompt_messages = create_prompt_messages(prompt_template, finding=finding)
    response = await client.chat.completions.create(  # type: ignore
        messages=prompt_messages,
        model=model_name,
    )
    if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
        return None

    out = DescribedFindingWithDetail(
        finding_name=finding.finding_name,
        synonyms=finding.synonyms,
        description=finding.description,
        detail=response.choices[0].message.content,
    )
    if response.citations:  # type: ignore
        out.citations = response.citations  # type: ignore

    # If the detail contains any URLs, we should add them to the citations
    if "http" in out.detail:
        if not out.citations:
            out.citations = []
        out.citations.extend([url for url in out.detail.split() if "http" in url])

    return out
