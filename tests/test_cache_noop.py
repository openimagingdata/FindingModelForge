from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.cache import RedisCache
from app.models import GitHubUser, User


@pytest.mark.asyncio
async def test_redis_cache_noop_behaviors():
    cache = RedisCache()  # client remains None (disabled), exercising no-op branches

    assert await cache.is_healthy() is False

    # Basic KV ops
    assert await cache.get("k") is None
    assert await cache.set("k", "v") is True
    assert await cache.exists("k") is False
    assert await cache.delete("k") is True

    # User caching APIs
    user = User(
        id=1,
        login="tester",
        name="Tester",
        email="t@example.com",
        avatar_url=None,
        html_url=None,
        organizations=["OIDM"],
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    assert await cache.set_user("1", user) is True
    assert await cache.delete_user("1") is True
    assert await cache.get_user("1") is None

    assert await cache.set_user_by_login(user) is True
    assert await cache.delete_user_by_login(user.login) is True
    assert await cache.get_user_by_login(user.login) is None

    # GitHub user data APIs
    gh = GitHubUser(
        id=99,
        login="octo",
        name="Octo",
        email=None,
        avatar_url=None,
        html_url=None,
        type="User",
        site_admin=False,
    )
    assert await cache.set_github_user_data(gh.id, gh) is True
    assert await cache.get_github_user_data(gh.id) is None

    # Finding model caches
    class DummyModel:
        def model_dump_json(self) -> str:
            return "{}"

    assert await cache.set_finding_model("slug", model_data=DummyModel()) is True  # type: ignore[arg-type]
    assert await cache.get_finding_model("slug") is None

    assert await cache.set_finding_models([{"name": "x"}]) is True
    assert await cache.get_finding_models() is None

    # Organizations cache (empty list path)
    assert await cache.set_organizations([]) is True
    assert await cache.get_organizations() is None
    await cache.invalidate_organizations_cache()

    # Invalidate list and stats
    await cache.invalidate_finding_models_cache("slug")
    stats = await cache.get_stats()
    assert isinstance(stats, dict) and stats.get("status") == "disconnected"


@pytest.mark.asyncio
async def test_invalidate_user_cache_noop():
    cache = RedisCache()
    user = User(
        id=2,
        login="another",
        name="Another",
        email=None,
        avatar_url=None,
        html_url=None,
        organizations=None,
        is_active=True,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
        updated_at=datetime(2024, 1, 1, tzinfo=UTC),
    )
    # Should not raise even when client is disabled
    await cache.invalidate_user_cache(user)
