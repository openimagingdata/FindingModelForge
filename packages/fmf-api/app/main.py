from fastapi.responses import RedirectResponse
from loguru import logger
from nicegui import app, ui

from .common.config import settings
from .gui.home import home_page
from .gui.login import login_page


@ui.page("/login")
async def login() -> None:
    login_page(ui)


@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=settings.login_path)
    else:
        home_page()


def startup():
    logger.info("Starting FMF API")


def shutdown():
    logger.info("Stopping FMF API")


app.on_startup(startup)
app.on_shutdown(shutdown)

print(settings.model_dump_json(indent=2))
ui.run(title="Finding Model Forge", storage_secret=settings.storage_secret.get_secret_value())
