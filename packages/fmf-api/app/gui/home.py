from typing import Any

from findingmodelforge.finding_info_tools import describe_finding_name
from findingmodelforge.models.finding_info import BaseFindingInfo
from loguru import logger
from nicegui import ui

from . import theme


def home_page():
    class State:
        def __init__(self) -> None:
            self.finding_name = ""
            self.running = False
            self.finding_description: BaseFindingInfo | None = None

        @property
        def model(self) -> dict[str, Any]:
            if self.finding_description:
                return self.finding_description.model_dump()
            return {}

    state = State()

    async def handle_submit():
        state.running = True

        state.finding_description = None
        logger.info("Describing: " + state.finding_name)
        described = await describe_finding_name(state.finding_name)
        logger.info("Described: " + described.model_dump_json())
        state.finding_description = described
        state.finding_name = ""
        state.running = False
        editor.properties = state.model
        editor.update()

    with theme.frame("Home"):
        ui.label("Welcome to Finding Model Forge!")

        with ui.row().classes("w-half"):
            ui.spinner().bind_visibility_from(state, "running")
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).on("keydown.enter", handle_submit).on(
                "blur", handle_submit
            )
        with ui.row():
            editor = ui.json_editor(state.model).bind_visibility_from(state, "finding_description")
