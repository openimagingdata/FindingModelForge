from fastapi.responses import RedirectResponse
from nicegui import app, ui

from .common.config import settings
from .gui.home import home_page
from .gui.login import login_page
from .routers import dummy


@ui.page("/login")
async def login() -> None:
    login_page(ui)


@ui.page("/")
async def index():
    if not app.storage.user.get("authenticated", False):
        return RedirectResponse(url=settings.login_path)
    else:
        home_page(ui)


app.include_router(dummy.router)

print(settings.model_dump_json(indent=2))
ui.run_with(app, title="Finding Model Forge", storage_secret=settings.storage_secret.get_secret_value())
