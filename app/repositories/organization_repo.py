"""Organization repository for contributor management.

Provides dual-source lookup:
- Index (canonical, read-only) - abstracts backend storage
- MongoDB (draft_organizations) - writable drafts

The Index class abstracts the storage backend completely.
We never reference the backend directly - only use Index API.
"""

from typing import Any

from findingmodel import Index
from findingmodel.contributor import Organization
from motor.motor_asyncio import AsyncIOMotorCollection


class OrganizationRepo:
    """Repository for Organization contributors with dual-source lookup.

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
            draft_collection: MongoDB collection for draft organizations
        """
        self.index = index  # Read-only canonical source
        self.draft_organizations = draft_collection  # Writable drafts
        self._cache: dict[str, Organization] = {}
        self._index_loaded = False  # Track if we've loaded from Index

    async def get_by_code(self, code: str) -> Organization | None:
        """Get Organization by code.

        Lookup order: cache → Index (canonical) → MongoDB (drafts) → None

        Note: Index class hides the storage backend implementation.
        We call index.get_organizations() and cache the results.

        Args:
            code: Organization code to lookup

        Returns:
            Organization if found, None otherwise
        """
        # 1. Check cache
        if code in self._cache:
            return self._cache[code]

        # 2. Load from Index if not cached yet (canonical source)
        # Index provides get_organizations() -> list[Organization]
        if not self._index_loaded:
            await self._load_from_index()

        if code in self._cache:
            return self._cache[code]

        # 3. Check MongoDB (draft organizations not yet in Index)
        doc = await self.draft_organizations.find_one({"code": code})
        if doc:
            org = Organization.model_validate(doc)
            self._cache[code] = org
            return org

        return None

    async def _load_from_index(self) -> None:
        """Load all organizations from Index into cache.

        Uses Index.get_organizations() which abstracts the storage backend.
        We never access the backend directly.
        """
        for org in await self.index.get_organizations():
            self._cache[org.code] = org
        self._index_loaded = True

    async def clear_cache(self) -> None:
        """Clear cache (e.g., when Index reloads with new data).

        Resets the _index_loaded flag to force reload from Index on next access.
        """
        self._cache.clear()
        self._index_loaded = False  # Force reload from Index on next access
