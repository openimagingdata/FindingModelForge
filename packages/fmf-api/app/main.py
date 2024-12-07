from fastapi.responses import RedirectResponse
from nicegui import app, ui

from .common.config import Config

from .gui.home import home_page
from .gui.login import login_page
from .routers import dummy


# Initialize the configuration once
Config.init()


@ui.page("/login")
async def login() -> None:
    login_page(ui)


@ui.page("/")
async def index() -> None:
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=Config.login_path)
    else:
        home_page(ui)


app.include_router(dummy.router)

ui.run_with(app, title="Finding Model Forge", storage_secret=Config.storage_secret)
