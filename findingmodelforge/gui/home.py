from findingmodel import FindingModelBase, FindingModelFull
from findingmodel.tools import (
    add_ids_to_finding_model,
    create_finding_model_from_markdown,
    create_finding_model_stub_from_finding_info,
    describe_finding_name,
)
from nicegui import binding, ui

from . import theme


@binding.bindable_dataclass
class State:
    running: bool = False
    finding_name: str | None = None
    show_markdown_in: bool = False
    markdown_in: str | None = None
    source: str = "MGBR"
    markdown: str = ""
    json: str = ""
    show_content: bool = False

    def reset(self) -> None:
        self.running = False
        self.finding_name = None
        self.show_markdown_in = False
        self.markdown_in = None
        self.source = "MGBR"
        self.markdown = ""
        self.json = ""
        self.show_content = False


def home_page() -> None:
    SOURCES = ["MGBR", "MSFT"]

    state = State()

    async def handle_submit() -> None:
        state.running = True
        if state.finding_name is None or state.finding_name == "":
            ui.notify("Please enter a finding name")
            state.running = False
            return
        finding_model: FindingModelFull | FindingModelBase
        if state.show_markdown_in:
            if state.markdown_in is None or state.markdown_in == "":
                ui.notify("Please enter finding information")
                state.running = False
                return
            finding_info = await describe_finding_name(state.finding_name)
            finding_model = await create_finding_model_from_markdown(
                finding_info, markdown_text=state.markdown_in.strip()
            )
        else:
            finding_info = await describe_finding_name(state.finding_name)
            finding_model = create_finding_model_stub_from_finding_info(finding_info)
        finding_model = add_ids_to_finding_model(finding_model, source=state.source)
        state.markdown = finding_model.as_markdown()
        state.json = finding_model.model_dump_json(indent=2, exclude_none=True, by_alias=True)
        state.show_content = bool(state.markdown) or bool(state.json)
        state.running = False

    with theme.frame("Home"), ui.column().classes("w-4/5 center"):
        with ui.row():
            ui.label("Create Finding Model").classes("text-2xl font-bold")
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
            ).props('input-class="h-64 w-full"')
        with ui.row().classes("items-center"):
            ui.button("Submit").on_click(handle_submit).bind_visibility_from(state, "running", lambda x: not x)
            # TODO: Clean up the display of the spinner
            ui.spinner(type="cube", size="lg").bind_visibility_from(state, "running")
        with ui.row().classes("w-full").bind_visibility_from(state, "show_content"):
            with ui.tabs().classes("w-full") as tabs:
                markdown = ui.tab("Markdown").bind_enabled_from(state, "markdown", bool)
                json = ui.tab("JSON").bind_enabled_from(state, "json", bool)
            with ui.tab_panels(tabs, value=markdown).classes("w-full"):
                with ui.tab_panel(markdown):
                    ui.markdown().bind_content_from(state, "markdown")
                with ui.tab_panel(json):
                    ui.code(language="json").bind_content_from(state, "json")
