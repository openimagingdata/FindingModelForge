from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from nicegui import app, ui
import requests

from . import theme
from ..common.config import Config


def login_page(ui):
    class State:
        def __init__(self) -> None:
            self.username = ""
            self.password = ""
            self.running = False

    state = State()

    with theme.frame("Login"):
        with ui.card().classes("fixed-center"):
            ui.spinner().bind_visibility_from(state, "running")
            ui.label(text="Login").classes("font-bold text-2xl")
            ui.input(label="Username", placeholder="start typing").bind_value(
                state, "username"
            ).bind_enabled_from(state, "running", lambda x: not x).classes("w-full")
            ui.input(
                label="Password",
                placeholder="start typing",
                password=True,
                password_toggle_button=True,
            ).bind_value(state, "password").bind_enabled_from(
                state, "running", lambda x: not x
            ).classes(
                "w-full"
            )
            with ui.row().classes("w-full"):
                ui.button("Login", on_click=lambda: 1).props("flat").classes("disabled")
                ui.button(
                    "Login with Github",
                    on_click=lambda: ui.navigate.to(
                        target=f"{Config.github_authorize_url}?client_id={Config.client_id}",
                        new_tab=False,
                    ),
                ).props("flat")


@ui.page("/callback")
async def callback(request: Request):
    """
    Handles the callback from GitHub
    :param request: The request from GitHub"""
    code = request.query_params.get("code", "")
    print(code)
    # state = request.query_params.get("state", "")
    # if state != app.storage.user["state"]:
    #     ui.notify(message=f"Invalid state: {state}")
    #     return
    access_token = fetch_access_token(code)
    if user_data := fetch_user_data(access_token):
        app.storage.user["authenticated"] = True
        app.storage.user["data"] = user_data
        return RedirectResponse("/")
    else:
        return RedirectResponse(Config.login_path)


@ui.page("/logout")
def logout_page():
    app.storage.user.update({"authenticated": False})
    app.storage.user.update({"data": {}})
    return RedirectResponse(Config.login_path)


@app.get("/user-storage")
def get_user_storage():
    return JSONResponse(content=app.storage.user)


def fetch_access_token(code: str) -> str:
    """
    Fetches the access token from GitHub
    :param code: The code from GitHub
    :return: The access token"""
    response = requests.post(
        Config.github_access_token_url,
        headers={"Accept": "application/json"},
        data={
            "client_id": Config.client_id,
            "client_secret": Config.client_secret,
            "code": code,
        },
    )
    return response.json()["access_token"]


def fetch_user_data(access_token: str) -> dict:
    """
    Fetches the user data from GitHub
    :param access_token: The access token
    :return: The user data"""
    response = requests.get(
        Config.github_user_info_url,
        headers={"Authorization": f"token {access_token}"},
    )
    return response.json()
