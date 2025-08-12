from __future__ import annotations

from datetime import UTC, datetime

import pytest
from bson import ObjectId

from app.database import DraftRepo


class _FakeCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *_args, **_kwargs):  # type: ignore[no-untyped-def]
        return self

    def limit(self, _n):  # type: ignore[no-untyped-def]
        return self

    def __aiter__(self):  # type: ignore[no-untyped-def]
        async def gen():
            for d in self._docs:
                yield d

        return gen()


class _FakeCollection:
    def __init__(self, docs):
        self._docs = docs

    def find(self, _query):  # type: ignore[no-untyped-def]
        return _FakeCursor(self._docs)


class _FakeDB:  # minimal duck type for AsyncIOMotorDatabase
    def __init__(self, docs):
        self.finding_model_drafts = _FakeCollection(docs)


@pytest.mark.asyncio
async def test_find_latest_by_name_returns_most_recent_doc():
    now = datetime.now(UTC)
    oid = ObjectId()
    docs = [
        {
            "_id": oid,
            "user_id": 1,
            "name": "Nodule",
            "created_at": now,
            "updated_at": now,
            "inputs": {"description": "d", "synonyms": ["s"], "attributes_markdown": "# a"},
            "generated_json": None,
            "status": "submitted",
            "action_log": [],
        }
    ]
    repo = DraftRepo(_FakeDB(docs))  # type: ignore[arg-type]
    got = await repo.find_latest_by_name(user_id=1, name="nodule")
    assert got is not None
    assert got.name.lower() == "nodule"
    assert got.status == "submitted"


@pytest.mark.asyncio
async def test_find_editable_by_name_filters_and_returns_doc():
    now = datetime.now(UTC)
    oid = ObjectId()
    docs = [
        {
            "_id": oid,
            "user_id": 1,
            "name": "Nodule",
            "created_at": now,
            "updated_at": now,
            "inputs": {"description": "d", "synonyms": ["s"], "attributes_markdown": "# a"},
            "generated_json": None,
            "status": "draft",
            "action_log": [],
        }
    ]
    repo = DraftRepo(_FakeDB(docs))  # type: ignore[arg-type]
    got = await repo.find_editable_by_name(user_id=1, name="NODULE")
    assert got is not None
    assert got.status == "draft"
