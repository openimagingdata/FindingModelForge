from nicegui import app, ui

from .gui.home import home_page
from .routers import dummy


@ui.page("/")
def index() -> None:
    home_page(ui)


app.include_router(dummy.router)

ui.run(title="Finding Model Forge")
