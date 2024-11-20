from findingmodelforge.config import (
    check_ready_for_mongodb,
    check_ready_for_openai,
    check_ready_for_perplexity,
    settings,
)


def test_settings_loaded(monkeypatch):
    settings_to_check = [
        "OPENAI_API_KEY",
        "PERPLEXITY_API_KEY",
        "PERPLEXITY_BASE_URL",
        "MONGO_DSN",
        "DATABASE_NAME",
    ]
    for setting in settings_to_check:
        monkeypatch.setattr(settings, setting, "test_value")
        assert settings.get(setting, None) is not None


def test_check_ready_for_openai(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "test_openai_key")
    assert check_ready_for_openai() is True

    monkeypatch.setattr(settings, "OPENAI_API_KEY", None)
    assert check_ready_for_openai() is False


def test_check_ready_for_perplexity(monkeypatch):
    monkeypatch.setattr(settings, "PERPLEXITY_API_KEY", "test_perplexity_key")
    monkeypatch.setattr(settings, "PERPLEXITY_BASE_URL", "test_perplexity_url")
    assert check_ready_for_perplexity() is True

    monkeypatch.setattr(settings, "PERPLEXITY_API_KEY", None)
    assert check_ready_for_perplexity() is False

    monkeypatch.setattr(settings, "PERPLEXITY_API_KEY", "test_perplexity_key")
    monkeypatch.setattr(settings, "PERPLEXITY_BASE_URL", None)
    assert check_ready_for_perplexity() is False


def test_check_ready_for_mongodb(monkeypatch):
    monkeypatch.setattr(settings, "MONGO_DSN", "test_mongo_dsn")
    monkeypatch.setattr(settings, "DATABASE_NAME", "test_database_name")
    assert check_ready_for_mongodb() is True

    monkeypatch.setattr(settings, "MONGO_DSN", None)
    assert check_ready_for_mongodb() is False

    monkeypatch.setattr(settings, "MONGO_DSN", "test_mongo_dsn")
    monkeypatch.setattr(settings, "DATABASE_NAME", None)
    assert check_ready_for_mongodb() is False
