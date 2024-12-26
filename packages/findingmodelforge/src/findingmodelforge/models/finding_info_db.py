import datetime

import pymongo
from beanie import Document, Insert, Replace, SaveChanges, Update, before_event
from pydantic import Field

from .finding_info import DetailedFindingInfo


def get_current_datetime():
    return datetime.datetime.now(datetime.UTC)


class FindingInfoDb(DetailedFindingInfo, Document):
    """The definition of a radiology finding with details on the attributes that a radiologist might use to
    characterize the finding in a radiology report. This class is used to store finding definitions in the database."""

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

    @before_event(Insert)
    def set_created_at(self):
        self.created_at = get_current_datetime()

    @before_event(Update, Replace, SaveChanges)
    def set_updated_at(self):
        self.updated_at = get_current_datetime()

    class Settings:
        name = "finding_infos"
        indexes = [
            pymongo.IndexModel("name", unique=True),
        ]
        keep_nulls = False
