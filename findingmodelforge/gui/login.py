from typing import Any

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from nicegui import app, ui

from findingmodelforge.common.config import settings

from . import theme


def login_page() -> None:
    ui.add_head_html('<link href="https://unpkg.com/eva-icons@1.1.3/style/eva-icons.css" rel="stylesheet" />')
    with theme.frame("Login"), ui.card().classes("fixed-center w-1/4"):
        ui.label(text="Login").classes("font-bold text-2xl centered")
        with ui.row().classes("w-full"):
            ui.button(
                "Login with Github",
                icon="eva-github",
                on_click=lambda: ui.navigate.to(
                    target=f"{settings.github_authorize_url}?client_id={settings.github_client_id}",
                    new_tab=False,
                ),
            ).classes("w-full text-lg font-bold")


@ui.page("/callback")
def callback(request: Request) -> RedirectResponse:
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
def logout_page() -> RedirectResponse:
    app.storage.user.update({"authenticated": False})
    app.storage.user.update({"data": {}})
    return RedirectResponse(settings.login_path)


# TODO: Only enable this in development environments
@app.get("/user-storage")
def get_user_storage() -> JSONResponse:
    return JSONResponse(content=app.storage.user)


def fetch_access_token(code: str) -> str:
    """
    Fetches the access token from GitHub
    :param code: The code from GitHub
    :return: The access token"""
    # TODO: Make this asynchronous
    assert settings.github_client_secret, "GitHub client secret is not set"
    response = httpx.post(
        settings.github_access_token_url,
        headers={"Accept": "application/json"},
        data={
            "client_id": settings.github_client_id,
            "client_secret": settings.github_client_secret.get_secret_value(),
            "code": code,
        },
    )
    if response.status_code != 200:
        raise Exception(f"Failed to fetch access token: {response.text}")
    if "access_token" not in response.json():
        raise Exception(f"Access token not found in response: {response.text}")
    assert isinstance(response.json(), dict)
    token = str(response.json().get("access_token"))
    if not token:
        raise Exception(f"Access token not found in response: {response.text}")
    return token


def fetch_user_data(access_token: str) -> dict[str, Any]:
    """
    Fetches the user data from GitHub
    :param access_token: The access token
    :return: The user data"""
    # TODO: Make this asynchronous
    response = httpx.get(
        settings.github_user_info_url,
        headers={"Authorization": f"token {access_token}"},
    )
    if response.status_code != 200:
        raise Exception(f"Failed to fetch user data: {response.text}")

    user_data = response.json()
    # Assert that the user data is a dictionary with string keys
    assert isinstance(user_data, dict)
    assert all(isinstance(key, str) for key in user_data)
    return user_data
