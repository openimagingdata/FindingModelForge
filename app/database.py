"""Database configuration and repository classes."""

from datetime import UTC, datetime
from typing import Any

from findingmodel.contributor import Organization, Person
from findingmodel.index import Index
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .config import settings
from .models import User, UserCreate, UserUpdate


class Database:
    """Database connection manager."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient[Any] | None = None
        self.db: AsyncIOMotorDatabase[Any] | None = None
        self.user_repo: UserRepo | None = None
        self.finding_index: Index | None = None
        self.people: dict[str, Person] = {}
        self.organizations: dict[str, Organization] = {}

    async def connect(self) -> None:
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.user_repo = UserRepo(self.db)

        # Initialize finding index with the same database client
        self.finding_index = Index(client=self.client, db_name=settings.mongodb_db)
        await self._load_people_and_organizations()

    async def _load_people_and_organizations(self) -> None:
        """Load people and organizations into memory."""
        assert self.finding_index is not None, "Finding index is not initialized"
        people_cursor = self.finding_index.people_collection.find()
        self.people.clear()
        async for person in people_cursor:
            if "github_username" in person:
                self.people[person["github_username"]] = Person.model_validate(person)
        organizations_cursor = self.finding_index.organizations_collection.find()
        self.organizations.clear()
        async for organization in organizations_cursor:
            self.organizations[organization["code"]] = Organization.model_validate(organization)

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
        self.user_repo = None
        self.finding_index = None


class UserRepo:
    """User repository for MongoDB operations."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.collection = db.users

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        now = datetime.now(UTC)
        user_dict = user_data.model_dump()
        user_dict.update(
            {
                "is_active": True,
                "organizations": [],
                "created_at": now,
                "updated_at": now,
            }
        )

        try:
            result = await self.collection.insert_one(user_dict)
            if result.inserted_id:
                user = await self.get_user(user_data.id)
                if user:
                    return user
        except DuplicateKeyError:
            # User already exists, return existing user
            user = await self.get_user(user_data.id)
            if user:
                return user

        raise ValueError("Failed to create user")

    async def get_user(self, user_id: int) -> User | None:
        """Get user by GitHub ID."""
        user_dict = await self.collection.find_one({"id": user_id})
        if user_dict:
            # Remove MongoDB's _id field
            user_dict.pop("_id", None)
            return User.model_validate(user_dict)
        return None

    async def get_user_by_login(self, login: str) -> User | None:
        """Get user by GitHub login/username."""
        user_dict = await self.collection.find_one({"login": login})
        if user_dict:
            # Remove MongoDB's _id field
            user_dict.pop("_id", None)
            return User.model_validate(user_dict)
        return None

    async def update_user(self, user_id: int, user_update: UserUpdate) -> User | None:
        """Update user information."""
        update_data = {k: v for k, v in user_update.model_dump().items() if v is not None}
        if not update_data:
            return await self.get_user(user_id)

        update_data["updated_at"] = datetime.now(UTC)

        result = await self.collection.update_one({"id": user_id}, {"$set": update_data})

        if result.modified_count > 0:
            return await self.get_user(user_id)
        return None

    async def deactivate_user(self, user_id: int) -> bool:
        """Deactivate a user."""
        result = await self.collection.update_one(
            {"id": user_id}, {"$set": {"is_active": False, "updated_at": datetime.now(UTC)}}
        )
        return bool(result.modified_count > 0)
