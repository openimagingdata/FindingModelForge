"""Database configuration and repository classes."""

# ruff: noqa: I001

from datetime import UTC, datetime
import re
from typing import Any

import humanize

from bson import ObjectId
from findingmodel.contributor import Organization, Person
from findingmodel.index import Index
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .config import logger, settings
from .models import (
    Comment,
    CommentThread,
    DraftStatus,
    FindingModelDraft,
    FindingModelInputs,
    User,
    UserCommentEntry,
    UserCreate,
    UserUpdate,
)


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

    async def ensure_person_for_user(self, user: "User") -> Person:
        """Create or get a Person for a User.

        Args:
            user: User object to create/get Person for

        Returns:
            Person object (existing or newly created)
        """
        if not self.finding_index:
            raise RuntimeError("Finding index not initialized")

        # Check if Person already exists in memory cache
        if user.login in self.people:
            return self.people[user.login]

        # Check if Person exists in database using the Index's people_collection
        existing_person = await self.finding_index.people_collection.find_one({"github_username": user.login})

        if existing_person:
            person = Person.model_validate(existing_person)
            self.people[user.login] = person
            return person

        # Create new Person from User data
        # Default organization code - could be enhanced to detect from user orgs
        org_code = "INDV"  # Individual contributor by default

        person_data = {
            "github_username": user.login,
            "email": user.email or f"{user.login}@users.noreply.github.com",
            "name": user.name or user.login,
            "organization_code": org_code,
            "url": user.html_url,
        }

        # Insert into database using the Index's people_collection
        await self.finding_index.people_collection.insert_one(person_data)

        # Create Person object and cache it
        person = Person.model_validate(person_data)
        self.people[user.login] = person

        logger.info(f"Created new Person for user {user.login}")
        return person

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
        user: User | None = None,
    ) -> FindingModelDraft:
        """Create or update a draft owned by the user.

        - Inserts a new draft when draft_id is None (status = "draft").
        - Updates state when draft_id provided and status is "draft" or "public" for the owner.
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
            # Populate author fields if user is provided
            if user is not None:
                set_doc["author_username"] = user.login
                set_doc["author_name"] = user.name
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
            # Populate author fields if user is provided
            if user is not None:
                set_doc["author_username"] = user.login
                set_doc["author_name"] = user.name
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
            # Allow updating drafts with status "draft" or "public" (but not "submitted")
            # Fixed to allow authors to edit their public drafts
            res = await self.collection.update_one(
                {"_id": oid, "user_id": user_id, "status": {"$in": ["draft", "public"]}}, update
            )
            if res.matched_count == 0:
                raise ValueError("Draft not found or not editable")

        return await self._load_by_oid(oid)

    async def get_draft(self, draft_id: str, user_id: int | None = None) -> FindingModelDraft | None:
        """Get draft, optionally checking ownership when user_id is provided.

        Users can view drafts if:
        - They own the draft (any status)
        - The draft is PUBLIC or SUBMITTED (even if they don't own it)
        """
        try:
            oid = ObjectId(draft_id)
        except Exception:
            return None

        # First, try to get the draft without any user restriction
        doc = await self.collection.find_one({"_id": oid})
        if not doc:
            return None

        draft = self._to_model(doc)

        # If no user_id provided, return the draft (used for public access)
        if user_id is None:
            return draft

        # If user owns the draft, they can always view it
        if draft.user_id == user_id:
            return draft

        # If user doesn't own it, they can only view PUBLIC or SUBMITTED drafts
        if draft.status in [DraftStatus.PUBLIC, DraftStatus.SUBMITTED]:
            return draft

        # Otherwise, access denied (return None)
        return None

    async def get_draft_with_author(self, draft_id: str, user_id: int | None = None) -> dict[str, Any] | None:
        """Get draft with author information.

        Since drafts now have embedded author fields (author_username, author_name),
        this method simply retrieves the draft and returns it as a dictionary.

        Args:
            draft_id: Draft ID to retrieve
            user_id: Optional user ID for ownership verification

        Returns:
            Draft dictionary if found and accessible, None otherwise
        """
        draft = await self.get_draft(draft_id, user_id)
        if draft is None:
            return None
        return draft.model_dump()

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
        """Delete draft when status is 'draft' or 'public' and owner matches."""
        try:
            oid = ObjectId(draft_id)
        except Exception:
            return False
        res = await self.collection.delete_one({"_id": oid, "user_id": user_id, "status": {"$in": ["draft", "public"]}})
        return bool(res.deleted_count)

    async def make_public(self, draft_id: str, user_id: int) -> FindingModelDraft:
        """Transition draft from 'draft' to 'public'."""
        try:
            oid = ObjectId(draft_id)
        except Exception as e:
            raise ValueError("Invalid draft id") from e
        now = datetime.now(UTC)
        res = await self.collection.update_one(
            {"_id": oid, "user_id": user_id, "status": DraftStatus.DRAFT},
            {
                "$set": {"status": DraftStatus.PUBLIC, "updated_at": now},
                "$push": {
                    "action_log": {
                        "timestamp": now,
                        "user_id": user_id,
                        "action": "status.changed",
                        "details": {"from_status": "draft", "to_status": "public"},
                    }
                },
            },
        )
        if res.matched_count == 0:
            raise ValueError("Draft not found or not in draft status")
        return await self._load_by_oid(oid)

    async def submit(self, draft_id: str, user_id: int) -> FindingModelDraft:
        """Transition draft from 'public' to 'submitted' and freeze edits."""
        try:
            oid = ObjectId(draft_id)
        except Exception as e:
            raise ValueError("Invalid draft id") from e
        now = datetime.now(UTC)
        res = await self.collection.update_one(
            {"_id": oid, "user_id": user_id, "status": DraftStatus.PUBLIC},
            {
                "$set": {"status": DraftStatus.SUBMITTED, "updated_at": now},
                "$push": {
                    "action_log": {
                        "timestamp": now,
                        "user_id": user_id,
                        "action": "status.changed",
                        "details": {"from_status": "public", "to_status": "submitted"},
                    }
                },
            },
        )
        if res.matched_count == 0:
            raise ValueError("Draft not found or not in public status")
        return await self._load_by_oid(oid)

    async def get_public_drafts(self) -> list[dict[str, Any]]:
        """Get all public drafts with author information for display.

        Returns:
            List of draft dictionaries with author_info and updated_display fields
        """
        # Simple query for public drafts, sorted by updated_at
        cursor = self.collection.find({"status": DraftStatus.PUBLIC.value}, sort=[("updated_at", -1)])
        drafts = await cursor.to_list(length=100)

        # Get unique user IDs for author lookup
        user_ids = set()
        for draft_doc in drafts:
            if "user_id" in draft_doc:
                user_ids.add(draft_doc["user_id"])

        # Lookup author information
        users_by_id = {}
        if user_ids:
            users_cursor = self.db.users.find({"id": {"$in": list(user_ids)}})
            async for user_doc in users_cursor:
                users_by_id[user_doc["id"]] = {"name": user_doc.get("name"), "github_username": user_doc.get("login")}

        # Convert to dicts and add display formatting
        result = []
        for draft_doc in drafts:
            # Store user_id before modifying draft_doc
            user_id = draft_doc.get("user_id")

            # Convert _id to id for Pydantic model
            if "_id" in draft_doc:
                draft_doc["id"] = str(draft_doc["_id"])
                del draft_doc["_id"]
            draft = FindingModelDraft(**draft_doc)
            draft_dict = draft.model_dump()

            # Add author information
            if user_id in users_by_id:
                draft_dict["author_info"] = users_by_id[user_id]
            else:
                # Fallback to embedded author fields if they exist
                author_info = {}
                if draft.author_name:
                    author_info["name"] = draft.author_name
                if draft.author_username:
                    author_info["github_username"] = draft.author_username

                if author_info:
                    draft_dict["author_info"] = author_info
                else:
                    # Default fallback
                    draft_dict["author_info"] = {"name": "Unknown", "github_username": None}

            # Add display formatting
            draft_dict["updated_display"] = humanize.naturaltime(
                datetime.now(UTC) - draft.updated_at.replace(tzinfo=UTC)
            )

            result.append(draft_dict)

        return result

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

    async def add_comment_to_index(self, user_id: int, entry: UserCommentEntry) -> None:
        """Add a comment entry to user's comment index for rate limiting.

        Args:
            user_id: GitHub user ID
            entry: UserCommentEntry with comment details
        """
        await self.collection.update_one({"id": user_id}, {"$push": {"comment_index": entry.model_dump(mode="json")}})


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

        # Log the reply data being saved
        reply_data = reply.model_dump(mode="json")
        logger.info(
            f"Saving reply to MongoDB: reply_id={reply_data.get('id')}, "
            + f"user_id={reply_data.get('user_id')}, parent_id={parent_id}",
        )

        # Update the thread by adding reply to the parent's replies array
        result = await self.collection.update_one(
            {"_id": ObjectId(thread_id), "comments.id": parent_id},
            {
                "$push": {"comments.$.replies": reply_data},
                "$inc": {"comment_count": 1},
                "$set": {"updated_at": now},
            },
        )

        success = bool(result.modified_count > 0)
        logger.info(f"Reply save result: success={success}, modified_count={result.modified_count}")
        return success

    async def report_comment(self, thread_id: str, comment_id: str, user_id: int) -> bool:
        """Mark comment as reported.
        Uses $set with array filters, $inc for reported_count.
        Only reports comments that haven't been reported yet.
        """
        if not ObjectId.is_valid(thread_id):
            return False

        now = datetime.now(UTC)

        # Try to update a top-level comment first
        # Only update if comment exists and hasn't been reported yet
        result = await self.collection.update_one(
            {
                "_id": ObjectId(thread_id),
                "comments": {
                    "$elemMatch": {"id": comment_id, "$or": [{"reported": {"$exists": False}}, {"reported": False}]}
                },
            },
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
        # Only update if reply exists and hasn't been reported yet
        result = await self.collection.update_one(
            {
                "_id": ObjectId(thread_id),
                "comments.replies": {
                    "$elemMatch": {"id": comment_id, "$or": [{"reported": {"$exists": False}}, {"reported": False}]}
                },
            },
            {
                "$set": {
                    "comments.$[comment].replies.$[reply].reported": True,
                    "comments.$[comment].replies.$[reply].reported_by": user_id,
                    "comments.$[comment].replies.$[reply].reported_at": now,
                },
                "$inc": {"reported_count": 1},
            },
            array_filters=[
                {"comment.replies.id": comment_id},
                {"reply.id": comment_id, "$or": [{"reply.reported": {"$exists": False}}, {"reply.reported": False}]},
            ],
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
