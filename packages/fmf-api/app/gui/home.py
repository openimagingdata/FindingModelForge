from findingmodelforge.finding_info_tools import describe_finding_name
from nicegui import ui

from . import theme


def home_page():
    state = {"running": False, "finding_name": None, "finding_description": None, "synonyms": None}

    async def handle_submit():
        state["running"] = True
        state["finding_description"] = None
        described_finding = await describe_finding_name(state["finding_name"])
        state["finding_description"] = described_finding.description
        if described_finding.synonyms:
            state["synonyms"] = ", ".join(described_finding.synonyms)
        state["running"] = False

    with theme.frame("Home"):
        with ui.row():
            ui.label("Welcome to Finding Model Forge!")
        with ui.row():
            ui.spinner().bind_visibility_from(state, "running")
            ui.input(label="Finding name", placeholder="start typing").bind_value(
                state, "finding_name"
            ).bind_enabled_from(state, "running", lambda x: not x).on("keydown.enter", handle_submit).on(
                "blur", handle_submit
            )
        with ui.row().bind_visibility_from(state, "finding_description"), ui.column():
            ui.label().bind_text_from(state, "synonyms", lambda x: f"Synonyms: {x}")
            ui.label("Description")
            ui.label().bind_text_from(state, "finding_description")
