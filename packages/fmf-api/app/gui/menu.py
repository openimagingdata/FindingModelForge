from nicegui import app, ui

SAMPLE_USER_DATA = {
    "login": "talkasab",
    "id": 42889,
    "node_id": "MDQ6VXNlcjQyODg5",
    "avatar_url": "https://avatars.githubusercontent.com/u/42889?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/talkasab",
    "html_url": "https://github.com/talkasab",
    "followers_url": "https://api.github.com/users/talkasab/followers",
    "following_url": "https://api.github.com/users/talkasab/following{/other_user}",
    "gists_url": "https://api.github.com/users/talkasab/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/talkasab/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/talkasab/subscriptions",
    "organizations_url": "https://api.github.com/users/talkasab/orgs",
    "repos_url": "https://api.github.com/users/talkasab/repos",
    "events_url": "https://api.github.com/users/talkasab/events{/privacy}",
    "received_events_url": "https://api.github.com/users/talkasab/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": False,
    "name": "Tarik Alkasab",
    "company": None,
    "blog": "",
    "location": "Boston, MA",
    "email": "tarik@alkasab.org",
    "hireable": None,
    "bio": None,
    "twitter_username": None,
    "notification_email": "tarik@alkasab.org",
    "public_repos": 18,
    "public_gists": 9,
    "followers": 24,
    "following": 8,
    "created_at": "2008-12-27T15:53:49Z",
    "updated_at": "2024-12-07T20:03:27Z",
}


def menu() -> None:
    user_profile = app.storage.user.get("data", None)
    if not app.storage.user.get("authenticated", False):
        ui.link("Login", "/login").classes(replace="text-white")
    else:
        ui.label("Logged in as " + user_profile["name"]).classes(replace="text-white")
        if user_profile["avatar_url"]:
            ui.avatar("img:" + user_profile["avatar_url"], color="blue")
        ui.link("Logout", "/logout").classes(replace="text-white")
        ui.link("Home", "/").classes(replace="text-white")
        ui.link("A", "/a").classes(replace="text-white")
        ui.link("B", "/b").classes(replace="text-white")
        ui.link("C", "/c").classes(replace="text-white")
