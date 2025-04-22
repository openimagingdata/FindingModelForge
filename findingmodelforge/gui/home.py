from findingmodel.tools import (
    add_ids_to_finding_model,
    create_finding_model_from_markdown,
    create_finding_model_stub_from_finding_info,
    describe_finding_name,
)
from nicegui import ui

from . import theme


def home_page() -> None:
    SOURCES = ["MGBR", "MSFT"]

    state = {
        "running": False,
        "finding_name": None,
        "show_markdown_in": False,
        "markdown_in": "",
        "source": "MGBR",
        "markdown": "",
        "json": "",
        "show_content": False,
    }

    async def handle_submit() -> None:
        state["running"] = True
        state["finding_description"] = None
        # TODO: Validate the form and show an error message if we don't have what we need
        finding_info = await describe_finding_name(state["finding_name"])
        # TODO: Check for errors, and put an error message display if relevant
        if markdown := state.get("markdown_id", ""):
            assert isinstance(markdown, str)
            finding_model = await create_finding_model_from_markdown(finding_info, markdown_text=markdown.strip())
        else:
            finding_model = create_finding_model_stub_from_finding_info(finding_info)
        finding_model = add_ids_to_finding_model(finding_model, source=state["source"])
        state["markdown"] = finding_model.as_markdown()
        state["json"] = finding_model.model_dump_json(indent=2, exclude_none=True, by_alias=True)
        state["show_content"] = state["markdown"] or state["json"]
        state["running"] = False

    with theme.frame("Home"), ui.column().classes("w-4/5 center"):
        with ui.row():
            ui.label("Finding Model Forge").classes("text-2xl font-bold")
        with ui.row().classes("w-full"):
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).classes("w-1/2")
            # .on("keydown.enter", handle_submit).on("blur", handle_submit)
            ui.select(label="Source", options=SOURCES).bind_value(state, "source").bind_enabled_from(
                state, "running", lambda x: not x
            )
            ui.switch("Add description").bind_value(state, "show_markdown_in")
        with ui.row().classes("w-full border rounded p-2").bind_visibility_from(state, "show_markdown_in"):
            ui.textarea(
                label="Finding information (Markdown)",
            ).bind_value(state, "markdown_in").bind_enabled_from(state, "running", lambda x: not x).classes(
                "w-full"
            ).props('input-class="h-96 w-full"')
        with ui.row():
            ui.button("Submit").on_click(handle_submit).bind_enabled_from(state, "running", lambda x: not x)
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
