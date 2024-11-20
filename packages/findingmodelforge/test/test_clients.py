import pytest
from findingmodelforge.clients import ConfigurationError, get_async_instructor_client, get_async_perplexity_client
from findingmodelforge.config import settings


def test_get_async_instructor_client():
    # Make sure settings are configured for OpenAI
    settings.__setattr__("OPENAI_API_KEY", "test_openai_key")
    client = get_async_instructor_client()
    assert client is not None
    # Add additional assertions to verify the client's functionality


def test_get_async_instructor_client_no_openai_key():
    # Make sure settings are not configured for OpenAI
    settings.__setattr__("OPENAI_API_KEY", None)
    with pytest.raises(ConfigurationError):
        _ = get_async_instructor_client()


def test_get_async_perplexity_client():
    # Make sure settings are configured for Perplexity
    settings.__setattr__("PERPLEXITY_API_KEY", "test_perplexity_key")
    settings.__setattr__("PERPLEXITY_BASE_URL", "test_perplexity_url")
    client = get_async_perplexity_client()
    assert client is not None


def test_get_async_perplexity_client_no_perplexity_key():
    # Make sure settings are not configured for Perplexity
    settings.__setattr__("PERPLEXITY_API_KEY", None)
    settings.__setattr__("PERPLEXITY_BASE_URL", "test_perplexity_url")
    with pytest.raises(ConfigurationError):
        _ = get_async_perplexity_client()
