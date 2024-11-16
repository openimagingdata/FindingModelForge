from typing import Any

import instructor
from dynaconf import settings  # type: ignore
from instructor import AsyncInstructor
from openai import AsyncOpenAI
from pydantic import BaseModel, Field


class DescribedFinding(BaseModel):
    finding_name: str = Field(..., title="Finding Name", description="The name of the finding")
    description: str = Field(..., title="Description", description="The description of the finding")


def get_async_client() -> AsyncInstructor:
    return instructor.from_openai(AsyncOpenAI(api_key=settings.OPENAI_API_KEY))


async def describe_finding_name(finding_name: str, model_name: str = "gpt-3.5-turbo") -> DescribedFinding | Any:
    client = get_async_client()
    result = await client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": """You are a radiology informatics assistant helping a radiologist write a textbook.
                    You are very good at understanding the properties of radiology findings and can help the radiologist flesh
                    out information about the findings.""",  # noqa: E501
            },
            {
                "role": "user",
                "content": f'Create a one-to-two sentence definition/description for: "{finding_name}"',
            },
        ],
        model=model_name,
        response_model=DescribedFinding,
    )
    return result
