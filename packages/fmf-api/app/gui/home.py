from findingmodelforge.finding_info_tools import describe_finding_name
from findingmodelforge.finding_model_tools import create_finding_model_stub_from_finding_info
from nicegui import ui

from . import theme


def home_page():
    state = {"running": False, "finding_name": None, "markdown": "", "json": "", "show_content": False}

    async def handle_submit():
        state["running"] = True
        state["finding_description"] = None
        finding_info = await describe_finding_name(state["finding_name"])
        # TODO: Check for errors, and put an error message display if relevant
        finding_model = create_finding_model_stub_from_finding_info(finding_info)
        state["markdown"] = finding_model.as_markdown()
        state["json"] = finding_model.model_dump_json(indent=2, exclude_none=True, by_alias=True)
        state["show_content"] = state["markdown"] or state["json"]
        state["running"] = False

    with theme.frame("Home"):
        with ui.row():
            ui.label("Welcome to Finding Model Forge!")
        with ui.row():
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).on("keydown.enter", handle_submit).on(
                "blur", handle_submit
            )
            # TODO: Clean up the display of the spinner
            ui.spinner().bind_visibility_from(state, "running")
        with ui.row().classes("w-full").bind_visibility_from(state, "show_content"):
            with ui.tabs().classes("w-full") as tabs:
                markdown = ui.tab("Markdown").bind_enabled_from(state, "markdown", bool)
                json = ui.tab("JSON").bind_enabled_from(state, "json", bool)
            with ui.tab_panels(tabs, value=markdown).classes("w-full"):
                with ui.tab_panel(markdown):
                    ui.markdown().bind_content_from(state, "markdown")
                with ui.tab_panel(json):
                    ui.code(language="json").bind_content_from(state, "json")
