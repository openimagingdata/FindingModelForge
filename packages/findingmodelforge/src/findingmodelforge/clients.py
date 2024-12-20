import instructor
from instructor import AsyncInstructor
from openai import AsyncOpenAI

from findingmodelforge import settings


def get_async_instructor_client() -> AsyncInstructor:
    settings.check_ready_for_openai()
    return instructor.from_openai(AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value()))  # type: ignore


def get_async_perplexity_client() -> AsyncOpenAI:
    settings.check_ready_for_perplexity()
    return AsyncOpenAI(
        api_key=str(settings.perplexity_api_key.get_secret_value()), base_url=str(settings.perplexity_base_url)
    )
