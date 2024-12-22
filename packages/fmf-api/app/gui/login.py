import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from nicegui import app, ui

from ..common.config import settings
from . import theme


def login_page():
    with theme.frame("Login"), ui.card().classes("fixed-center"):
        ui.label(text="Login").classes("font-bold text-2xl")
        with ui.row().classes("w-full"):
            # TODO: Add the github icon in here
            ui.button(
                "Login with Github",
                on_click=lambda: ui.navigate.to(
                    target=f"{settings.github_authorize_url}?client_id={settings.github_client_id}",
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
        # TODO: Figure out if we already know this user, and if not, put them in our database
        return RedirectResponse("/")
    else:
        return RedirectResponse(settings.login_path)


@ui.page("/logout")
def logout_page():
    app.storage.user.update({"authenticated": False})
    app.storage.user.update({"data": {}})
    return RedirectResponse(settings.login_path)


# TODO: Only enable this in development environments
@app.get("/user-storage")
def get_user_storage():
    return JSONResponse(content=app.storage.user)


def fetch_access_token(code: str) -> str:
    """
    Fetches the access token from GitHub
    :param code: The code from GitHub
    :return: The access token"""
    # TODO: Make this asynchronous
    response = httpx.post(
        settings.github_access_token_url,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret.get_secret_value(),
            "code": code,
        },
    )
    return response.json()["access_token"]


def fetch_user_data(access_token: str) -> dict:
    """
    Fetches the user data from GitHub
    :param access_token: The access token
    :return: The user data"""
    response = httpx.get(
        settings.github_user_info_url,
        headers={"Authorization": f"token {access_token}"},
    )
    return response.json()
