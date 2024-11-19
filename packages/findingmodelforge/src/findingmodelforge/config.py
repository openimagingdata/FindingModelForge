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


# Not working yet
