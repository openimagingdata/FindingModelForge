from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from loguru import logger
from nicegui import app, ui

from .common.config import settings
from .gui.home import home_page
from .gui.login import login_page


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting app")
    logger.warning("Starting app")
    yield
    print("Stopping app")
    logger.warning("Stopping app")


main = FastAPI(lifespan=lifespan)


@ui.page("/login")
async def login() -> None:
    login_page(ui)


@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=settings.login_path)
    else:
        home_page(ui)


print(settings.model_dump_json(indent=2))
ui.run_with(main, title="Finding Model Forge", storage_secret=settings.storage_secret.get_secret_value())
