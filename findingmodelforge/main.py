from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger
from nicegui import App, app, ui

from .common.config import settings
from .gui import theme
from .gui.home import home_page
from .gui.login import login_page


def startup(app: App) -> None:
    logger.info("Starting FMF Web App")


def shutdown() -> None:
    logger.info("Shutting down FMF Web App")


app.on_startup(startup)
app.on_shutdown(shutdown)


@ui.page("/login")
def login() -> None:
    login_page()


@ui.page("/")
def index() -> RedirectResponse | None:
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=settings.login_path)
    with theme.frame("Home"):
        home_page()
    return None


anvil_svg = (Path(__file__).parent / "anvil.svg").read_text()
print(settings.model_dump_json(indent=2))
print(anvil_svg)
ui.run_with(
    FastAPI(),
    title="Finding Model Forge",
    storage_secret=settings.storage_secret.get_secret_value(),
    favicon=anvil_svg,
    dark=True,
)
