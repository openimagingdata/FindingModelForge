from enum import StrEnum

from findingmodel import FindingModelBase, FindingModelFull
from findingmodel.contributor import Person
from findingmodel.tools import (
    add_ids_to_finding_model,
    add_standard_codes_to_finding_model,
    create_finding_model_from_markdown,
    create_finding_model_stub_from_finding_info,
    describe_finding_name,
)
from nicegui import app, binding, ui

from . import theme


class CreateMode(StrEnum):
    STUB = "Stub"
    FROM_TEXT = "From Text"

    @classmethod
    def choices(cls) -> list[str]:
        return [cls.STUB, cls.FROM_TEXT]

    @classmethod
    def default(cls) -> "CreateMode":
        return cls.STUB

    @classmethod
    def from_str(cls, value: str) -> "CreateMode":
        if value in cls.choices():
            return cls[value]
        raise ValueError(f"Invalid mode: {value}")

    @classmethod
    def value_map(cls) -> dict[str, "CreateMode"]:
        return {
            "Stub": cls.STUB,
            "From Text": cls.FROM_TEXT,
        }


DEFAULT_MARKDOWN_IN = """
- Presence: absent, present, unknown, indeterminate
- Change from prior: unchanged, stable, new, resolved, increased, decreased, larger, smaller
"""


@binding.bindable_dataclass
class State:
    running: bool = False
    finding_name: str | None = None
    create_mode: CreateMode = CreateMode.default()
    markdown_in: str = DEFAULT_MARKDOWN_IN
    source: str = "MGB"
    markdown: str = ""
    json: str = ""
    show_content: bool = False
    show_profile_completion: bool = False
    user_email: str = ""
    user_name: str = ""

    @property
    def enable_controls(self) -> bool:
        return not self.running


def home_page() -> None:
    SOURCES = ["MGB", "MSFT", "ACR"]

    state = State()
    print(state)

    # Check if we have all required user information
    user_email = app.storage.user.get("notification_email") or app.storage.user.get("user_email")
    user_name = app.storage.user.get("user_name")
    user_login = app.storage.user.get("user_login")

    # Initialize state with current values
    state.user_email = user_email or ""
    state.user_name = user_name or ""

    # Check if profile completion is needed
    state.show_profile_completion = not all([user_email, user_name, user_login])

    def get_contributor() -> Person:
        """Get the contributor Person object using current data."""
        github_username = app.storage.user.get("user_login") or ""
        name = app.storage.user.get("user_name") or app.storage.user.get("user_email") or ""
        email = app.storage.user.get("notification_email") or app.storage.user.get("user_email") or ""

        return Person(
            github_username=github_username,
            name=name,
            email=email,
            organization_code=state.source,
        )

    def handle_profile_save() -> None:
        """Save the profile completion information."""
        if not state.user_email or not state.user_name:
            ui.notify("Please fill in all required fields")
            return

        # Save to app storage
        app.storage.user["user_email"] = state.user_email
        app.storage.user["user_name"] = state.user_name
        # Also update notification_email if it was missing
        if not app.storage.user.get("notification_email"):
            app.storage.user["notification_email"] = state.user_email

        state.show_profile_completion = False
        ui.notify("Profile updated successfully!")

    async def handle_submit() -> None:
        # Check if profile completion is still needed
        if state.show_profile_completion:
            ui.notify("Please complete your profile information first")
            return

        state.running = True
        if state.finding_name is None or state.finding_name == "":
            ui.notify("Please enter a finding name")
            state.running = False
            return

        try:
            contributor = get_contributor()
            finding_model: FindingModelFull | FindingModelBase
            if state.create_mode == CreateMode.FROM_TEXT:
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
            add_standard_codes_to_finding_model(finding_model)
            finding_model.contributors = [contributor]
            state.markdown = finding_model.as_markdown()
            state.json = finding_model.model_dump_json(indent=2, exclude_none=True, by_alias=True)
            state.show_content = bool(state.markdown) or bool(state.json)
        except Exception as e:
            ui.notify(f"Error creating finding model: {e!s}")
        finally:
            state.running = False

    with theme.frame("Home"), ui.column().classes("w-full lg:w-4/5 mx-auto border rounded p-4"):
        # Profile completion section
        with ui.card().classes("w-full").bind_visibility_from(state, "show_profile_completion"):
            ui.label("Complete Your Profile").classes("text-xl font-bold text-center")
            ui.label("Please provide the required information to create finding models:").classes("text-center")
            with ui.row().classes("w-full"):
                ui.input(label="Your Name", placeholder="Enter your full name").bind_value(state, "user_name").classes(
                    "w-1/2"
                )
                ui.input(label="Email Address", placeholder="Enter your email").bind_value(state, "user_email").classes(
                    "w-1/2"
                )
            with ui.row().classes("w-full justify-center"):
                ui.button("Save Profile", on_click=handle_profile_save).classes("primary")

        # Main finding model creation section
        with ui.column().classes("w-full").bind_visibility_from(state, "show_profile_completion", lambda x: not x):
            with ui.row():
                ui.label("Create Finding Model").classes("text-2xl font-bold")
            with ui.row().classes("w-full"):
                ui.label("Create mode").classes("text-lg font-bold")
                ui.toggle(CreateMode.value_map(), value=CreateMode.STUB).bind_value(
                    state, "create_mode"
                ).bind_enabled_from(state, "enable_controls")

            with ui.row().classes("w-full"):
                ui.input(label="Finding name", placeholder="start typing").bind_value(
                    state, "finding_name"
                ).bind_enabled_from(state, "running", lambda x: not x).classes("w-1/2")
                # .on("keydown.enter", handle_submit).on("blur", handle_submit)
            with (
                ui.row()
                .classes("w-full border rounded p-2")
                .bind_visibility_from(state, "create_mode", lambda x: x == CreateMode.FROM_TEXT)
            ):
                ui.textarea(label="Finding information (Markdown)").bind_value(state, "markdown_in").bind_enabled_from(
                    state, "running", lambda x: not x
                ).classes("w-full").props(
                    'input-class="h-64 w-full" input-style="font-size: 1.1rem; font-family: monospace;"'
                )
            with ui.row().classes("w-full items-center"):
                ui.label("Contributor: " + app.storage.user["user_login"]).classes("text-lg font-bold")
                ui.select(label="Source", options=SOURCES).bind_value(state, "source").bind_enabled_from(
                    state, "running", lambda x: not x
                )
            with ui.row().classes("items-center"):
                ui.button("Submit").on_click(handle_submit).bind_visibility_from(state, "running", lambda x: not x)
                ui.spinner(type="cube", size="lg").bind_visibility_from(state, "running")
            with ui.row().classes("w-full").bind_visibility_from(state, "show_content"):
                with ui.tabs().classes("w-full") as tabs:
                    markdown = ui.tab("Markdown").bind_enabled_from(state, "markdown", bool)
                    json = ui.tab("JSON").bind_enabled_from(state, "json", bool)
                with ui.tab_panels(tabs, value=markdown).classes("w-full"):
                    with ui.tab_panel(markdown).classes("bg-slate-800 p-4 rounded"):
                        ui.markdown().bind_content_from(state, "markdown")
                    with ui.tab_panel(json).classes("bg-slate-800 p-4 rounded"):
                        ui.code(language="json").bind_content_from(state, "json").classes("overflow-auto block").style(
                            "max-width: 100%; white-space: pre-wrap;"
                        )
