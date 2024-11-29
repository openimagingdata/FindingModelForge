from typing import Any

from .clients import get_async_instructor_client, get_async_perplexity_client
from .config import settings
from .models.finding_info import BaseFindingInfo, DetailedFindingInfo
from .prompt_template import create_prompt_messages, load_prompt_template


async def describe_finding_name(
    finding_name: str, model_name: str = settings.openai_default_model
) -> BaseFindingInfo | Any:
    client = get_async_instructor_client()
    prompt_template = load_prompt_template("get_finding_description")
    messages = create_prompt_messages(prompt_template, finding_name=finding_name)
    result = await client.chat.completions.create(
        messages=messages,
        model=model_name,
        response_model=BaseFindingInfo,
    )
    return result


async def get_detail_on_finding(
    finding: BaseFindingInfo, model_name: str = settings.perplexity_default_model
) -> DetailedFindingInfo | None:
    client = get_async_perplexity_client()
    prompt_template = load_prompt_template("get_finding_detail")
    prompt_messages = create_prompt_messages(prompt_template, finding=finding)
    response = await client.chat.completions.create(  # type: ignore
        messages=prompt_messages,
        model=model_name,
    )
    if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
        return None

    out = DetailedFindingInfo(
        name=finding.name,
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
