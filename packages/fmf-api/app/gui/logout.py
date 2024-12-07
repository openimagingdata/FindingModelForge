import asyncio

from . import theme


def logout_page(ui):
    class State:
        def __init__(self) -> None:
            self.finding_name = ""
            self.running = False

    state = State()

    async def handle_submit():
        state.running = True
        await asyncio.sleep(1)
        ui.notify(f"Did a bunch of work with {state.finding_name}!")
        state.finding_name = ""
        state.running = False

    with theme.frame("Logout"):
        ui.label("Welcome to Finding Model Forge!")

        with ui.row():
            ui.spinner().bind_visibility_from(state, "running")
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).on(
                "keydown.enter", handle_submit
            ).on(
                "blur", handle_submit
            )
