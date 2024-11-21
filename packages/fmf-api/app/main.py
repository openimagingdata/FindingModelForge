from nicegui import app, ui

from .gui import theme
from .routers import dummy


@ui.page("/")
def home_page() -> None:
    with theme.frame("Home"):
        ui.label("Welcome to Finding Model Forge!")


app.include_router(dummy.router)

ui.run(title="Finding Model Forge")
