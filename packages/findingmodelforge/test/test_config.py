import pytest
from findingmodelforge import settings
from findingmodelforge.config import ConfigurationError
from pydantic import SecretStr


def test_settings_loaded():
    assert settings.openai_api_key.get_secret_value()
    assert settings.perplexity_api_key.get_secret_value()
    assert settings.perplexity_base_url
    assert settings.mongo_dsn.get_secret_value()
    assert settings.database_name


def test_check_ready_for_openai():
    assert settings.check_ready_for_openai()

    old_value = settings.openai_api_key
    settings.openai_api_key = SecretStr("")
    with pytest.raises(ConfigurationError):
        settings.check_ready_for_openai()
    settings.openai_api_key = old_value


def test_check_ready_for_perplexity():
    assert settings.check_ready_for_perplexity()

    old_value = settings.perplexity_api_key
    settings.perplexity_api_key = SecretStr("")
    with pytest.raises(ConfigurationError):
        settings.check_ready_for_perplexity()
    settings.perplexity_api_key = old_value


def test_check_ready_for_mongodb():
    assert settings.check_ready_for_mongodb()

    old_value = settings.mongo_dsn
    settings.mongo_dsn = SecretStr("")
    with pytest.raises(ConfigurationError):
        settings.check_ready_for_mongodb()
    settings.mongo_dsn = old_value

    old_value = settings.database_name
    settings.database_name = ""
    with pytest.raises(ConfigurationError):
        settings.check_ready_for_mongodb()
    settings.database_name = old_value
