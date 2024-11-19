from typing import Any

import instructor
from dynaconf import settings  # type: ignore
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field

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


def get_async_client() -> AsyncInstructor:
    try:
        api_key = settings.OPENAI_API_KEY
    except AttributeError:
        raise AttributeError("OPENAI_API_KEY is not set in the configuration") from None
    return instructor.from_openai(AsyncOpenAI(api_key=api_key))


def get_async_perplexity_client() -> AsyncOpenAI:
    try:
        api_key = settings.PERPLEXITY_API_KEY
        base_url = settings.PERPLEXITY_BASE_URL
    except AttributeError:
        raise AttributeError("PERPLEXITY_API_KEY and/or PERPLEXITY_BASE_URL not set in the configuration") from None
    return AsyncOpenAI(api_key=api_key, base_url=base_url)


async def describe_finding_name(finding_name: str, model_name: str = DEFAULT_OPENAI_MODEL) -> DescribedFinding | Any:
    client = get_async_client()
    result = await client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """You are a radiology informatics assistant helping a radiologist write a textbook.
                    You are very good at understanding the properties of radiology findings and can help the radiologist
                    flesh out information about the findings.""",
            },
            {
                "role": "user",
                "content": f"""Create a one-to-two sentence definition/description for the finding. 
                    If applicable, include synonyms as might be used by radiologists and other health 
                    care professionals, including acronyms.
                    
                    The description should be concise and use medical terminology; it's intended to be read by health 
                    care professionsals rather than laypersons.
                    
                    Finding to describe: {finding_name}""",
            },
        ],
        model=model_name,
        response_model=DescribedFinding,
    )
    return result


async def get_detail_on_finding(
    finding: DescribedFinding, model_name: str = DEFAULT_PERPLEXITY_MODEL
) -> DescribedFindingWithDetail | None:
    client = get_async_perplexity_client()
    response = await client.chat.completions.create(  # type: ignore
        messages=[
            {
                "role": "system",
                "content": """You are a radiology informatics assistant helping a radiologist write a textbook.
                    You are very good at understanding the properties of radiology findings and can help the radiologist
                    flesh out information about the findings.""",
            },
            {
                "role": "user",
                "content": f"""Get detailed information on this specifc finding. This should include information about 
                    the appearance of the finding on imaging studies, the clinical significance of the finding, 
                    and any other relevant information that a radiologist might use to characterize the finding 
                    in a radiology report.

                    Be specific about the characteristics/attributes that a radiologist uses to describe this finding
                    in a radiology report, including the actual words that might be used for different values those
                    attributes might take ("attributes")--these might be numeric values, or categorical values.

                    Especially include:
                    - Information on specific locations in the body where the finding can be seen ("locations").;
                    - Brief list of other findings that might be seen in association ("associated findings").

                    This will be read by radiologists, so you don't need to include general information on radiology
                    reporting or the basics of how to describe findings. Use medical terminology and language.

                    Especially favor results that come from Wikipedia, Radiopaedia, radassistant.nl, and other 
                    reputable sources. Also, use (and cite, if possible) review articles from journals such as 
                    Radiographics, Radiology, the American Journal of Roentgenology, and the European Journal of 
                    Radiology.

                    Specifically, if there's a Wikipedia page on the finding, make sure to include it in your response
                    and cite it.
                    
                    Finding to describe: {finding.finding_name}

                    Description: {finding.description}

                    Synonyms: {finding.synonyms}""",
            },
        ],
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
