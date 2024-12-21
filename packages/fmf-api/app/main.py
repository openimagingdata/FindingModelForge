from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger
from nicegui import app, ui

from app.gui.home import home_page

from .common.config import settings
from .gui import theme
from .gui.login import login_page


def startup(app):
    logger.info("Starting FMF Web App")


def shutdown():
    logger.info("Shutting down FMF Web App")


app.on_startup(startup)
app.on_shutdown(shutdown)


@ui.page("/login")
async def login() -> None:
    login_page()


@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=settings.login_path)
    with theme.frame("Home"):
        home_page()


print(settings.model_dump_json(indent=2))
ui.run_with(FastAPI(), title="Finding Model Forge", storage_secret=settings.storage_secret.get_secret_value())
