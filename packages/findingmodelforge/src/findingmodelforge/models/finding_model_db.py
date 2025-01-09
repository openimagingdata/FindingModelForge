import datetime
from typing import Sequence

import pymongo
from beanie import Delete, Document, Replace, Save, Update, after_event, before_event

# from beanie.operators import In
from bson.objectid import ObjectId
from pydantic import Field

from .finding_model import FindingModelBase
from .search_index import SearchIndex, SearchIndexRecord, SearchResult


def get_current_datetime():
    return datetime.datetime.now(datetime.UTC)


search_index = SearchIndex("finding_models")


class FindingModelDb(FindingModelBase, Document):  # type: ignore[misc]
    """The definition of a radiology finding with details on the attributes that a radiologist might use to
    characterize the finding in a radiology report. This class is used to store finding definitions in the database."""

    def __init__(self, **data):
        super().__init__(**data)

    active: bool = Field(
        default=True,
        title="Active",
        description="Whether the finding definition is active and should be used",  # noqa: E501
    )
    created_at: datetime.datetime = Field(
        default_factory=get_current_datetime,
        title="Created At",
        description="The date and time the finding definition was created",
    )
    updated_at: datetime.datetime | None = Field(
        default=None,
        title="Updated At",
        description="The date and time the finding definition was last updated",
    )

    @after_event(Save)
    def add_to_search_index(self):
        search_index.add_or_update_record(self.to_search_index_record())

    @after_event(Delete)
    def remove_from_search_index(self):
        assert self.id is not None
        search_index.remove_record(str(self.id))

    @before_event(Save, Update, Replace)
    def set_updated_at(self):
        self.updated_at = get_current_datetime()

    class Settings:
        name = "finding_models"
        indexes = [
            pymongo.IndexModel("name", unique=True),
        ]
        keep_nulls = False

    @classmethod
    async def get_many(cls, ids: list[str]) -> Sequence["FindingModelDb"]:
        obj_ids: list[ObjectId] = [ObjectId(id) for id in ids]
        return await cls.find({"_id": {"$in": obj_ids}}).to_list()

    @classmethod
    async def semantic_search(cls, query: str, top_k: int = 5) -> Sequence["FindingModelDb"]:
        results: Sequence[SearchResult] = await search_index.search(query, top_k=top_k)
        return await cls.get_many([r.model_id for r in results])

    def to_search_index_record(self) -> SearchIndexRecord:
        return SearchIndexRecord(
            model_id=str(self.id),
            name=self.name,
            tags=(list(self.tags) if self.tags else []),
            text=f"{self.name}\n\nDescription: {self.description}",
        )

    @classmethod
    async def initialize_search_index(cls):
        # Get all the records, turning them into SearchIndexRecord objects using an async list comprehension
        records = [doc.to_search_index_record() async for doc in cls.find()]
        await search_index.build_semantic_indices(records, drop_if_exists=True)
