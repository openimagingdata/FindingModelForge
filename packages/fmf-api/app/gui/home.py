from findingmodelforge.finding_info_tools import describe_finding_name
from findingmodelforge.models.finding_info import BaseFindingInfo

from . import theme


def home_page(ui):
    class State:
        def __init__(self) -> None:
            self.finding_name = ""
            self.running = False
            self.finding_description: BaseFindingInfo | None = None

    state = State()

    async def handle_submit():
        state.running = True
        state.finding_description = None
        described = await describe_finding_name(state.finding_name)
        print("Described: " + described.model_dump_json())
        state.finding_description = described
        state.finding_name = ""
        state.running = False

    with theme.frame("Home"):
        ui.label("Welcome to Finding Model Forge!")

        with ui.row():
            ui.spinner().bind_visibility_from(state, "running")
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).on("keydown.enter", handle_submit).on(
                "blur", handle_submit
            )
        with ui.row():
            json = state.finding_description.model_dump_json() if state.finding_description else ""
            ui.json_editor(json).bind_visibility_from(state, "finding_description")
