from contextlib import contextmanager

import findingmodelforge.clients as clients
import pytest
from findingmodelforge.config import ConfigurationError, settings
from pydantic import SecretStr


@contextmanager
def set_temp_api_keys(openai_api_key: str | None = None, perplexity_api_key: str | None = None):
    old_openai_api_key = settings.openai_api_key
    old_perplexity_api_key = settings.perplexity_api_key
    if openai_api_key is not None:
        settings.openai_api_key = SecretStr(openai_api_key)
    if perplexity_api_key is not None:
        settings.perplexity_api_key = SecretStr(perplexity_api_key)
    try:
        yield
    finally:
        settings.openai_api_key = old_openai_api_key
        settings.perplexity_api_key = old_perplexity_api_key


def test_get_async_instructor_client():
    client = clients.get_async_instructor_client()
    assert client is not None


def test_get_async_instructor_client_no_openai_key():
    # Make sure settings are not configured for OpenAI
    with set_temp_api_keys(openai_api_key=""), pytest.raises(ConfigurationError):
        _ = clients.get_async_instructor_client()


def test_get_async_perplexity_client():
    # Make sure settings are configured for Perplexity
    client = clients.get_async_perplexity_client()
    assert client is not None


def test_get_async_perplexity_client_no_perplexity_key():
    # Make sure settings are not configured for Perplexity
    with set_temp_api_keys(perplexity_api_key=""), pytest.raises(ConfigurationError):
        _ = clients.get_async_perplexity_client()
