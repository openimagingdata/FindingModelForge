from pathlib import Path

from dynaconf import Dynaconf  # type: ignore

settings = Dynaconf(
    root_path=Path(__file__).parent.parent,
    environments=True,
    envvar_prefix="FMF",
    settings_files=["settings.toml", ".secrets.toml"],
)

# `envvar_prefix` = export envvars with `export FMF_FOO=bar`.
# `settings_files` = Load these files in the order.
