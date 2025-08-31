"""Database configuration and repository classes."""

# ruff: noqa: I001

from datetime import UTC, datetime
import re
from typing import Any

from bson import ObjectId
from findingmodel.contributor import Organization, Person
from findingmodel.index import Index
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .config import settings
from .models import Comment, CommentThread, FindingModelDraft, FindingModelInputs, User, UserCreate, UserUpdate


class Database:
    """Database connection manager."""

    def __init__(self) -> None:
        self.client: AsyncIOMotorClient[Any] | None = None
        self.db: AsyncIOMotorDatabase[Any] | None = None
        self.user_repo: UserRepo | None = None
        self.draft_repo: DraftRepo | None = None
        self.comment_repo: CommentRepo | None = None
        self.finding_index: Index | None = None
        self.people: dict[str, Person] = {}
        self.organizations: dict[str, Organization] = {}

    async def connect(self) -> None:
        """Connect to MongoDB."""
        self.client = AsyncIOMotorClient(settings.mongodb_uri)
        self.db = self.client[settings.mongodb_db]
        self.user_repo = UserRepo(self.db)
        self.draft_repo = DraftRepo(self.db)
        self.comment_repo = CommentRepo(self.db)

        # Initialize finding index with the same database client
        self.finding_index = Index(client=self.client, db_name=settings.mongodb_db)

        # Create indices for comment threads collection
        comment_threads = self.db.comment_threads
        await comment_threads.create_index([("reference_type", 1), ("reference_id", 1)], unique=True)
        await comment_threads.create_index([("reported_count", -1)])

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
        self.draft_repo = None
        self.comment_repo = None
        self.finding_index = None


class DraftRepo:
    """Draft repository for MongoDB operations (skeleton)."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.collection = db.finding_model_drafts

    async def save_draft(
        self,
        user_id: int,
        name: str,
        inputs: FindingModelInputs,
        draft_id: str | None = None,
        generated_json: str | None = None,
    ) -> FindingModelDraft:
        """Create or update a draft owned by the user.

        - Inserts a new draft when draft_id is None (status = "draft").
        - Updates state when draft_id provided and status is "draft" for the owner.
        - Appends action_log entries accordingly.
        """
        now = datetime.now(UTC)
        # Normalize draft_id: empty string or whitespace should be treated as None (insert)
        if draft_id is not None and draft_id.strip() == "":
            draft_id = None

        if draft_id is None:
            # Upsert by (user_id, name, status='draft'): ensure uniqueness per user/name for editable drafts
            filter_doc = {"user_id": user_id, "name": name, "status": "draft"}
            set_doc: dict[str, Any] = {
                "name": name,
                "user_id": user_id,
                "updated_at": now,
                "inputs": inputs.model_dump(),
            }
            if generated_json is not None:
                set_doc["generated_json"] = generated_json
            update_doc = {
                "$setOnInsert": {
                    "created_at": now,
                    "status": "draft",
                },
                "$set": set_doc,
            }
            res = await self.collection.update_one(filter_doc, update_doc, upsert=True)
            upserted = res.upserted_id is not None
            if upserted:
                oid = res.upserted_id
            else:
                # Find the existing document's _id
                existing = await self.collection.find_one(filter_doc, {"_id": 1})
                if not existing or "_id" not in existing:
                    raise ValueError("Failed to locate upserted draft")
                oid = existing["_id"]

            # Append action log entries in a separate update to avoid operator conflicts
            created_entry = {
                "timestamp": now,
                "user_id": user_id,
                "action": "draft.created",
                "details": None,
            }
            saved_entry = {
                "timestamp": now,
                "user_id": user_id,
                "action": "draft.saved",
                "details": {"step": "edit-attributes"},
            }
            entries = [created_entry, saved_entry] if upserted else [saved_entry]
            await self.collection.update_one({"_id": oid}, {"$push": {"action_log": {"$each": entries}}})
        else:
            # Validate provided draft_id before using
            if not ObjectId.is_valid(draft_id):
                raise ValueError("Invalid draft id")
            oid = ObjectId(draft_id)
            set_doc = {
                "name": name,
                "inputs": inputs.model_dump(),
                "updated_at": now,
            }
            if generated_json is not None:
                set_doc["generated_json"] = generated_json
            update = {
                "$set": set_doc,
                "$push": {
                    "action_log": {
                        "timestamp": now,
                        "user_id": user_id,
                        "action": "draft.saved",
                        "details": {"step": "edit-attributes"},
                    }
                },
            }
            res = await self.collection.update_one({"_id": oid, "user_id": user_id, "status": "draft"}, update)
            if res.matched_count == 0:
                raise ValueError("Draft not found or not editable")

        return await self._load_by_oid(oid)

    async def get_draft(self, draft_id: str, user_id: int) -> FindingModelDraft | None:
        """Return draft if owned by user; otherwise None."""
        try:
            oid = ObjectId(draft_id)
        except Exception:
            return None
        doc = await self.collection.find_one({"_id": oid, "user_id": user_id})
        if not doc:
            return None
        return self._to_model(doc)

    async def list_for_user(self, user_id: int) -> list[FindingModelDraft]:
        """List drafts for a given user (may expand to involvement later)."""
        cursor = self.collection.find({"user_id": user_id}).sort("updated_at", -1)
        items: list[FindingModelDraft] = []
        async for doc in cursor:
            items.append(self._to_model(doc))
        return items

    async def find_editable_by_name(self, user_id: int, name: str) -> FindingModelDraft | None:
        """Find most recent editable draft for a user by inputs.name (case-insensitive)."""
        # Case-insensitive exact match on draft name
        pattern = re.compile(f"^{re.escape(name)}$", flags=re.IGNORECASE)
        cursor = (
            self.collection.find({"user_id": user_id, "status": "draft", "name": {"$regex": pattern}})
            .sort("updated_at", -1)
            .limit(1)
        )
        docs = [doc async for doc in cursor]
        if not docs:
            return None
        return self._to_model(docs[0])

    async def find_latest_by_name(self, user_id: int, name: str) -> FindingModelDraft | None:
        """Find most recent draft for a user by name, regardless of status (case-insensitive)."""
        pattern = re.compile(f"^{re.escape(name)}$", flags=re.IGNORECASE)
        cursor = self.collection.find({"user_id": user_id, "name": {"$regex": pattern}}).sort("updated_at", -1).limit(1)
        docs = [doc async for doc in cursor]
        if not docs:
            return None
        return self._to_model(docs[0])

    async def delete_draft(self, draft_id: str, user_id: int) -> bool:
        """Delete draft only when status is 'draft' and owner matches."""
        try:
            oid = ObjectId(draft_id)
        except Exception:
            return False
        res = await self.collection.delete_one({"_id": oid, "user_id": user_id, "status": "draft"})
        return bool(res.deleted_count)

    async def submit(self, draft_id: str, user_id: int) -> FindingModelDraft:
        """Transition draft from 'draft' to 'submitted' and freeze edits."""
        try:
            oid = ObjectId(draft_id)
        except Exception as e:
            raise ValueError("Invalid draft id") from e
        now = datetime.now(UTC)
        res = await self.collection.update_one(
            {"_id": oid, "user_id": user_id, "status": "draft"},
            {
                "$set": {"status": "submitted", "updated_at": now},
                "$push": {
                    "action_log": {
                        "timestamp": now,
                        "user_id": user_id,
                        "action": "status.changed",
                        "details": {"from_status": "draft", "to_status": "submitted"},
                    }
                },
            },
        )
        if res.matched_count == 0:
            raise ValueError("Draft not found or not in draft status")
        return await self._load_by_oid(oid)

    async def _load_by_oid(self, oid: ObjectId) -> FindingModelDraft:
        doc = await self.collection.find_one({"_id": oid})
        if not doc:
            raise ValueError("Draft not found after write")
        return self._to_model(doc)

    def _to_model(self, doc: dict[str, Any]) -> FindingModelDraft:
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return FindingModelDraft.model_validate(doc)


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


class CommentRepo:
    """Comment repository for MongoDB operations."""

    def __init__(self, db: AsyncIOMotorDatabase[Any]) -> None:
        self.db = db
        self.collection = db.comment_threads

    async def get_thread(self, reference_type: str, reference_id: str) -> CommentThread | None:
        """Get comment thread for a specific reference."""
        doc = await self.collection.find_one({"reference_type": reference_type, "reference_id": reference_id})
        if not doc:
            return None
        return self._to_model(doc)

    async def add_comment(self, reference_type: str, reference_id: str, comment: Comment) -> CommentThread:
        """Create thread if doesn't exist, add comment atomically.
        Uses $push for comments array, $inc for comment_count.
        """
        now = datetime.now(UTC)

        # Use upsert to create thread if it doesn't exist
        await self.collection.update_one(
            {"reference_type": reference_type, "reference_id": reference_id},
            {
                "$push": {"comments": comment.model_dump(mode="json")},
                "$inc": {"comment_count": 1},
                "$set": {"updated_at": now},
                "$setOnInsert": {
                    "id": str(ObjectId()),
                    "reference_type": reference_type,
                    "reference_id": reference_id,
                    "created_at": now,
                    "reported_count": 0,
                },
            },
            upsert=True,
        )

        # Get the updated thread
        doc = await self.collection.find_one({"reference_type": reference_type, "reference_id": reference_id})
        if not doc:
            raise RuntimeError("Failed to retrieve thread after update")
        return self._to_model(doc)

    async def add_reply(self, thread_id: str, parent_id: str, reply: Comment) -> bool:
        """Add reply to specific parent comment.
        Uses $push with array filters to add reply to correct parent.
        Single-level only - enforced by checking parent is top-level.
        """
        if not ObjectId.is_valid(thread_id):
            return False

        now = datetime.now(UTC)

        # First verify parent comment exists and is not itself a reply
        # (i.e., it's in the top-level comments array, not in someone's replies)
        thread_doc = await self.collection.find_one({"_id": ObjectId(thread_id), "comments.id": parent_id})
        if not thread_doc:
            return False

        # Find the parent comment and verify it's not a reply itself
        parent_comment = None
        for comment in thread_doc.get("comments", []):
            if comment["id"] == parent_id:
                parent_comment = comment
                break

        if not parent_comment:
            return False

        # Update the thread by adding reply to the parent's replies array
        result = await self.collection.update_one(
            {"_id": ObjectId(thread_id), "comments.id": parent_id},
            {
                "$push": {"comments.$.replies": reply.model_dump(mode="json")},
                "$inc": {"comment_count": 1},
                "$set": {"updated_at": now},
            },
        )

        return bool(result.modified_count > 0)

    async def report_comment(self, thread_id: str, comment_id: str, user_id: int) -> bool:
        """Mark comment as reported.
        Uses $set with array filters, $inc for reported_count.
        """
        if not ObjectId.is_valid(thread_id):
            return False

        now = datetime.now(UTC)

        # Try to update a top-level comment first
        result = await self.collection.update_one(
            {"_id": ObjectId(thread_id), "comments.id": comment_id},
            {
                "$set": {
                    "comments.$.reported": True,
                    "comments.$.reported_by": user_id,
                    "comments.$.reported_at": now,
                },
                "$inc": {"reported_count": 1},
            },
        )

        if result.modified_count > 0:
            return True

        # If not found in top-level, try replies using array filters
        # We need to use arrayFilters to update nested replies
        result = await self.collection.update_one(
            {"_id": ObjectId(thread_id), "comments.replies.id": comment_id},
            {
                "$set": {
                    "comments.$[comment].replies.$[reply].reported": True,
                    "comments.$[comment].replies.$[reply].reported_by": user_id,
                    "comments.$[comment].replies.$[reply].reported_at": now,
                },
                "$inc": {"reported_count": 1},
            },
            array_filters=[{"comment.replies.id": comment_id}, {"reply.id": comment_id}],
        )

        return bool(result.modified_count > 0)

    async def get_threads_with_reported(self) -> list[CommentThread]:
        """Find threads where reported_count > 0."""
        cursor = self.collection.find({"reported_count": {"$gt": 0}}).sort("reported_count", -1)
        threads: list[CommentThread] = []
        async for doc in cursor:
            threads.append(self._to_model(doc))
        return threads

    def _to_model(self, doc: dict[str, Any]) -> CommentThread:
        """Convert MongoDB document to CommentThread model."""
        doc = dict(doc)
        doc["id"] = str(doc.pop("_id"))
        return CommentThread.model_validate(doc)
