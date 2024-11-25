from pathlib import Path

from dynaconf import Dynaconf  # type: ignore

settings = Dynaconf(
    # Use development, testing, etc
    environments=True,
    # `settings_files` = Load these files in the order.
    settings_files=["settings.toml", ".secrets.toml"],
    root_path=Path(__file__).parent.parent,
    # `envvar_prefix` = export envvars with `export FMF_FOO=bar`
    envvar_prefix="FMF",
    load_dotenv=True,
    # `env_switcher` = switch environment with `export FMF_ENV=development`
    env_switcher="FMF_ENV",
)


class ConfigurationError(RuntimeError):
    pass


def _check_multiple_keys(*keys_to_check: str) -> bool:
    return all(settings.get(key, None) is not None for key in keys_to_check)


def check_ready_for_openai() -> bool:
    return _check_multiple_keys("OPENAI_API_KEY")


def check_ready_for_perplexity() -> bool:
    return _check_multiple_keys("PERPLEXITY_API_KEY", "PERPLEXITY_BASE_URL")


def check_ready_for_mongodb() -> bool:
    return _check_multiple_keys("MONGO_DSN", "DATABASE_NAME")
