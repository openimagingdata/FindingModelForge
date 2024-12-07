from nicegui import app, ui


def menu() -> None:
    if not app.storage.user.get("authenticated", False):
        ui.link("Login", "/login").classes(replace="text-white")
    else:
        ui.link("Logout", "/logout").classes(replace="text-white")
        ui.link("Home", "/").classes(replace="text-white")
        ui.link("A", "/a").classes(replace="text-white")
        ui.link("B", "/b").classes(replace="text-white")
        ui.link("C", "/c").classes(replace="text-white")
