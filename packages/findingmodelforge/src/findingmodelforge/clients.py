import instructor
from instructor import AsyncInstructor
from openai import AsyncOpenAI

from .config import check_ready_for_openai, check_ready_for_perplexity, settings


class ConfigurationError(RuntimeError):
    pass


def get_async_instructor_client() -> AsyncInstructor:
    if not check_ready_for_openai():
        raise ConfigurationError("OPENAI_API_KEY is not set in the configuration")
    return instructor.from_openai(AsyncOpenAI(api_key=settings.openai_api_key))  # type: ignore


def get_async_perplexity_client() -> AsyncOpenAI:
    if not check_ready_for_perplexity():
        raise ConfigurationError("PERPLEXITY_API_KEY and/or PERPLEXITY_BASE_URL not set in the configuration")
    return AsyncOpenAI(api_key=settings.perplexity_api_key, base_url=settings.perplexity_base_url)
