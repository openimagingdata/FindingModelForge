"""People repository for contributor management.

Provides dual-source lookup:
- Index (canonical, read-only) - abstracts backend storage
- MongoDB (draft_people) - writable drafts

The Index class abstracts the storage backend completely.
We never reference the backend directly - only use Index API.
"""

from typing import Any

from findingmodel import Index
from findingmodel.contributor import Person
from motor.motor_asyncio import AsyncIOMotorCollection

from app.models import User


class PeopleRepo:
    """Repository for Person contributors with dual-source lookup.

    Reads from Index (canonical, backend-agnostic) and MongoDB (drafts).
    Never writes to Index - it's read-only canonical data.
    """

    def __init__(
        self,
        index: Index,
        draft_collection: AsyncIOMotorCollection[Any],
    ) -> None:
        """Initialize repository with Index and draft collection.

        Args:
            index: Index instance (abstracts backend storage, read-only)
            draft_collection: MongoDB collection for draft people
        """
        self.index = index  # Read-only canonical source (abstracts backend)
        self.draft_people = draft_collection  # Writable drafts
        self._cache: dict[str, Person] = {}
        self._index_loaded = False  # Track if we've loaded from Index

    async def get_by_username(self, username: str) -> Person | None:
        """Get Person by github_username.

        Lookup order: cache → Index (canonical) → MongoDB (drafts) → None

        Note: Index class abstracts the storage backend implementation.
        We call index.get_people() and cache the results.

        Args:
            username: GitHub username to lookup

        Returns:
            Person if found, None otherwise
        """
        # 1. Check cache
        if username in self._cache:
            return self._cache[username]

        # 2. Load from Index if not cached yet (canonical source, takes precedence)
        # Index provides get_people() -> list[Person]
        # We load into cache on first access for O(1) lookups
        if not self._index_loaded:
            await self._load_from_index()

        if username in self._cache:
            return self._cache[username]

        # 3. Check MongoDB (draft contributors not yet in Index)
        doc = await self.draft_people.find_one({"github_username": username})
        if doc:
            person = Person.model_validate(doc)
            self._cache[username] = person
            return person

        return None

    async def _load_from_index(self) -> None:
        """Load all people from Index into cache.

        Uses Index.get_people() which abstracts the storage backend.
        We never access the backend directly.
        """
        for person in await self.index.get_people():
            self._cache[person.github_username] = person
        self._index_loaded = True

    async def ensure_for_user(self, user: User) -> Person:
        """Get or create Person for User.

        Writes only to MongoDB draft_people collection.
        Index is read-only - we never write to it.

        Args:
            user: User object to create/get Person for

        Returns:
            Person object (existing or newly created)
        """
        # Check if exists in Index or drafts
        if person := await self.get_by_username(user.login):
            return person

        # Create new draft person (MongoDB only, never Index)
        person_data = {
            "github_username": user.login,
            "email": user.email or f"{user.login}@users.noreply.github.com",
            "name": user.name or user.login,
            "organization_code": "OIDM",  # Individual by default
            "url": user.html_url,
        }
        await self.draft_people.insert_one(person_data)

        person = Person.model_validate(person_data)
        self._cache[user.login] = person
        return person

    async def clear_cache(self) -> None:
        """Clear cache (e.g., when Index reloads with new data).

        Resets the _index_loaded flag to force reload from Index on next access.
        """
        self._cache.clear()
        self._index_loaded = False  # Force reload from Index on next access
