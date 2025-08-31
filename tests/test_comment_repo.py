"""Unit tests for CommentRepo class."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.database import CommentRepo
from app.models import Comment, CommentThread


class TestCommentRepo:
    """Test CommentRepo class."""

    @pytest.fixture
    def mock_db(self) -> MagicMock:
        """Mock database."""
        db = MagicMock()
        db.comment_threads = MagicMock()  # Not AsyncMock for the collection itself
        # Set up the async methods as AsyncMock
        db.comment_threads.find_one = AsyncMock()
        db.comment_threads.update_one = AsyncMock()
        return db

    @pytest.fixture
    def comment_repo(self, mock_db: MagicMock) -> CommentRepo:
        """CommentRepo instance with mocked database."""
        return CommentRepo(mock_db)

    @pytest.fixture
    def sample_comment(self) -> Comment:
        """Sample comment for testing."""
        return Comment(
            id=str(uuid4()),
            user_id=12345,
            user_name="testuser",
            user_avatar_url="https://avatar.example.com/testuser.jpg",
            content="This is a test comment",
            created_at=datetime.now(UTC),
        )

    @pytest.fixture
    def sample_thread_doc(self) -> dict:
        """Sample MongoDB thread document."""
        return {
            "_id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "comment_count": 1,
            "reported_count": 0,
            "comments": [
                {
                    "id": str(uuid4()),
                    "user_id": 12345,
                    "user_name": "testuser",
                    "user_avatar_url": "https://avatar.example.com/testuser.jpg",
                    "content": "Test comment",
                    "created_at": datetime.now(UTC),
                    "replies": [],
                    "reported": False,
                    "reported_by": None,
                    "reported_at": None,
                }
            ],
        }

    async def test_get_thread_existing(self, comment_repo: CommentRepo, mock_db: MagicMock, sample_thread_doc: dict):
        """Test getting existing thread."""
        mock_db.comment_threads.find_one.return_value = sample_thread_doc

        thread = await comment_repo.get_thread("finding_model", "oifm_123")

        assert thread is not None
        assert isinstance(thread, CommentThread)
        assert thread.id == "507f1f77bcf86cd799439011"
        assert thread.reference_type == "finding_model"
        assert thread.reference_id == "oifm_123"
        assert thread.comment_count == 1
        assert len(thread.comments) == 1

        mock_db.comment_threads.find_one.assert_called_once_with(
            {"reference_type": "finding_model", "reference_id": "oifm_123"}
        )

    async def test_get_thread_not_found(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test getting thread that doesn't exist."""
        mock_db.comment_threads.find_one.return_value = None

        thread = await comment_repo.get_thread("finding_model", "nonexistent")

        assert thread is None
        mock_db.comment_threads.find_one.assert_called_once_with(
            {"reference_type": "finding_model", "reference_id": "nonexistent"}
        )

    async def test_add_comment_new_thread(self, comment_repo: CommentRepo, mock_db: MagicMock, sample_comment: Comment):
        """Test adding comment to create new thread."""
        # Mock the upsert operation
        mock_db.comment_threads.update_one = AsyncMock()

        # Mock the follow-up find_one to return the created thread
        created_thread_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "comment_count": 1,
            "reported_count": 0,
            "comments": [sample_comment.model_dump(mode="json")],
        }
        mock_db.comment_threads.find_one.return_value = created_thread_doc

        thread = await comment_repo.add_comment("finding_model", "oifm_123", sample_comment)

        # Verify upsert was called with correct parameters
        mock_db.comment_threads.update_one.assert_called_once()
        call_args = mock_db.comment_threads.update_one.call_args

        # Check filter
        assert call_args[0][0] == {"reference_type": "finding_model", "reference_id": "oifm_123"}

        # Check update operations
        update_ops = call_args[0][1]
        assert "$push" in update_ops
        assert "$inc" in update_ops
        assert "$set" in update_ops
        assert "$setOnInsert" in update_ops

        assert update_ops["$push"]["comments"] == sample_comment.model_dump(mode="json")
        assert update_ops["$inc"]["comment_count"] == 1
        assert "updated_at" in update_ops["$set"]

        # Check upsert flag
        assert call_args[1]["upsert"] is True

        # Verify result
        assert isinstance(thread, CommentThread)
        assert thread.comment_count == 1
        assert len(thread.comments) == 1

    async def test_add_comment_existing_thread(
        self, comment_repo: CommentRepo, mock_db: MagicMock, sample_comment: Comment
    ):
        """Test adding comment to existing thread."""
        mock_db.comment_threads.update_one = AsyncMock()

        # Create a properly formatted existing comment
        existing_comment = {
            "id": "existing_comment",
            "user_id": 99999,
            "user_name": "existing_user",
            "user_avatar_url": "https://example.com/avatar.jpg",
            "content": "Existing comment",
            "created_at": datetime.now(UTC),
            "replies": [],
            "reported": False,
            "reported_by": None,
            "reported_at": None,
        }

        existing_thread_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "comment_count": 2,
            "reported_count": 0,
            "comments": [existing_comment, sample_comment.model_dump(mode="json")],
        }
        mock_db.comment_threads.find_one.return_value = existing_thread_doc

        thread = await comment_repo.add_comment("finding_model", "oifm_123", sample_comment)

        # Should still call upsert even for existing thread
        mock_db.comment_threads.update_one.assert_called_once()
        assert isinstance(thread, CommentThread)
        assert thread.comment_count == 2

    async def test_add_comment_failed_retrieval(
        self, comment_repo: CommentRepo, mock_db: MagicMock, sample_comment: Comment
    ):
        """Test add_comment when thread retrieval fails after update."""
        mock_db.comment_threads.update_one = AsyncMock()
        mock_db.comment_threads.find_one.return_value = None

        with pytest.raises(RuntimeError, match="Failed to retrieve thread after update"):
            await comment_repo.add_comment("finding_model", "oifm_123", sample_comment)

    async def test_add_reply_success(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test successfully adding reply to top-level comment."""
        thread_id = "507f1f77bcf86cd799439011"
        parent_id = "parent_comment_id"

        # Mock ObjectId.is_valid to return True and ObjectId() to return the thread_id
        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            # Mock finding the parent comment
            thread_doc = {
                "comments": [
                    {"id": parent_id, "content": "Parent comment"},
                    {"id": "other_comment", "content": "Other comment"},
                ]
            }
            mock_db.comment_threads.find_one.return_value = thread_doc

            # Mock successful update
            mock_update_result = MagicMock()
            mock_update_result.modified_count = 1
            mock_db.comment_threads.update_one.return_value = mock_update_result

            reply = Comment(
                user_id=67890,
                user_name="replier",
                content="This is a reply",
                created_at=datetime.now(UTC),
            )

            result = await comment_repo.add_reply(thread_id, parent_id, reply)

            assert result is True

            # Verify parent lookup was called
            mock_db.comment_threads.find_one.assert_called_once_with(
                {"_id": mock_objectid_instance, "comments.id": parent_id}
            )

            # Verify reply update was called
            mock_db.comment_threads.update_one.assert_called_once()
            call_args = mock_db.comment_threads.update_one.call_args

            assert call_args[0][0] == {"_id": mock_objectid_instance, "comments.id": parent_id}
            update_ops = call_args[0][1]
            assert "$push" in update_ops
            assert "$inc" in update_ops
            assert "$set" in update_ops
            assert update_ops["$push"]["comments.$.replies"] == reply.model_dump(mode="json")
            assert update_ops["$inc"]["comment_count"] == 1

    async def test_add_reply_invalid_thread_id(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test add_reply with invalid thread ID."""
        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = False

            reply = Comment(
                user_id=67890,
                user_name="replier",
                content="This is a reply",
                created_at=datetime.now(UTC),
            )

            result = await comment_repo.add_reply("invalid_id", "parent_id", reply)

            assert result is False
            mock_db.comment_threads.find_one.assert_not_called()

    async def test_add_reply_parent_not_found(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test add_reply when parent comment not found."""
        thread_id = "507f1f77bcf86cd799439011"

        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            # Mock thread not found
            mock_db.comment_threads.find_one.return_value = None

            reply = Comment(
                user_id=67890,
                user_name="replier",
                content="This is a reply",
                created_at=datetime.now(UTC),
            )

            result = await comment_repo.add_reply(thread_id, "nonexistent_parent", reply)

            assert result is False
            mock_db.comment_threads.update_one.assert_not_called()

    async def test_add_reply_update_failed(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test add_reply when database update fails."""
        thread_id = "507f1f77bcf86cd799439011"
        parent_id = "parent_comment_id"

        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            thread_doc = {"comments": [{"id": parent_id, "content": "Parent comment"}]}
            mock_db.comment_threads.find_one.return_value = thread_doc

            # Mock failed update
            mock_update_result = MagicMock()
            mock_update_result.modified_count = 0
            mock_db.comment_threads.update_one.return_value = mock_update_result

            reply = Comment(
                user_id=67890,
                user_name="replier",
                content="This is a reply",
                created_at=datetime.now(UTC),
            )

            result = await comment_repo.add_reply(thread_id, parent_id, reply)

            assert result is False

    async def test_report_comment_top_level_success(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test successfully reporting top-level comment."""
        thread_id = "507f1f77bcf86cd799439011"
        comment_id = "comment_to_report"
        user_id = 99999

        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            # Mock successful top-level update
            mock_update_result = MagicMock()
            mock_update_result.modified_count = 1
            mock_db.comment_threads.update_one.return_value = mock_update_result

            result = await comment_repo.report_comment(thread_id, comment_id, user_id)

            assert result is True

            # Should only call update_one once for top-level
            assert mock_db.comment_threads.update_one.call_count == 1

            call_args = mock_db.comment_threads.update_one.call_args
            assert call_args[0][0] == {"_id": mock_objectid_instance, "comments.id": comment_id}

            update_ops = call_args[0][1]
            assert "$set" in update_ops
            assert "$inc" in update_ops
            assert update_ops["$set"]["comments.$.reported"] is True
            assert update_ops["$set"]["comments.$.reported_by"] == user_id
            assert "comments.$.reported_at" in update_ops["$set"]
            assert update_ops["$inc"]["reported_count"] == 1

    async def test_report_comment_reply_success(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test successfully reporting reply comment."""
        thread_id = "507f1f77bcf86cd799439011"
        comment_id = "reply_to_report"
        user_id = 99999

        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            # Mock failed top-level update (comment not found)
            mock_update_result_1 = MagicMock()
            mock_update_result_1.modified_count = 0

            # Mock successful reply update
            mock_update_result_2 = MagicMock()
            mock_update_result_2.modified_count = 1

            mock_db.comment_threads.update_one.side_effect = [mock_update_result_1, mock_update_result_2]

            result = await comment_repo.report_comment(thread_id, comment_id, user_id)

            assert result is True

            # Should call update_one twice (top-level failed, reply succeeded)
            assert mock_db.comment_threads.update_one.call_count == 2

            # Check second call (reply update)
            second_call_args = mock_db.comment_threads.update_one.call_args_list[1]
            assert second_call_args[0][0] == {"_id": mock_objectid_instance, "comments.replies.id": comment_id}

            update_ops = second_call_args[0][1]
            assert "$set" in update_ops
            assert "$inc" in update_ops
            assert "comments.$[comment].replies.$[reply].reported" in update_ops["$set"]
            assert update_ops["$set"]["comments.$[comment].replies.$[reply].reported"] is True

            # Check array filters
            assert "array_filters" in second_call_args[1]
            array_filters = second_call_args[1]["array_filters"]
            assert {"comment.replies.id": comment_id} in array_filters
            assert {"reply.id": comment_id} in array_filters

    async def test_report_comment_invalid_thread_id(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test report_comment with invalid thread ID."""
        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = False

            result = await comment_repo.report_comment("invalid_id", "comment_id", 99999)

            assert result is False
            mock_db.comment_threads.update_one.assert_not_called()

    async def test_report_comment_not_found(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test reporting comment that doesn't exist."""
        thread_id = "507f1f77bcf86cd799439011"

        with patch("app.database.ObjectId") as mock_objectid_class:
            mock_objectid_class.is_valid.return_value = True
            mock_objectid_instance = MagicMock()
            mock_objectid_class.return_value = mock_objectid_instance

            # Mock both updates fail (comment not found)
            mock_update_result = MagicMock()
            mock_update_result.modified_count = 0
            mock_db.comment_threads.update_one.return_value = mock_update_result

            result = await comment_repo.report_comment(thread_id, "nonexistent_comment", 99999)

            assert result is False
            # Should try both top-level and reply updates
            assert mock_db.comment_threads.update_one.call_count == 2

    async def test_get_threads_with_reported(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test getting threads with reported comments."""
        sample_docs = [
            {
                "_id": "thread1",
                "reference_type": "finding_model",
                "reference_id": "oifm_1",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "comment_count": 2,
                "reported_count": 3,
                "comments": [],
            },
            {
                "_id": "thread2",
                "reference_type": "draft",
                "reference_id": "draft_1",
                "created_at": datetime.now(UTC),
                "updated_at": datetime.now(UTC),
                "comment_count": 1,
                "reported_count": 1,
                "comments": [],
            },
        ]

        # Create a simple AsyncIterator mock
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self.items)
                except StopIteration:
                    raise StopAsyncIteration from None

        mock_cursor = MockAsyncIterator(sample_docs)

        # Mock the chain: find() returns an object with sort() that returns the cursor
        mock_find_result = MagicMock()
        mock_find_result.sort.return_value = mock_cursor
        mock_db.comment_threads.find.return_value = mock_find_result

        threads = await comment_repo.get_threads_with_reported()

        assert len(threads) == 2
        assert all(isinstance(thread, CommentThread) for thread in threads)
        assert threads[0].id == "thread1"
        assert threads[0].reported_count == 3
        assert threads[1].id == "thread2"
        assert threads[1].reported_count == 1

        # Verify query
        mock_db.comment_threads.find.assert_called_once_with({"reported_count": {"$gt": 0}})
        mock_find_result.sort.assert_called_once_with("reported_count", -1)

    async def test_get_threads_with_reported_empty(self, comment_repo: CommentRepo, mock_db: MagicMock):
        """Test getting threads with reported comments when none exist."""

        # Create empty AsyncIterator
        class MockAsyncIterator:
            def __init__(self, items):
                self.items = iter(items)

            def __aiter__(self):
                return self

            async def __anext__(self):
                try:
                    return next(self.items)
                except StopIteration:
                    raise StopAsyncIteration from None

        mock_cursor = MockAsyncIterator([])

        mock_find_result = MagicMock()
        mock_find_result.sort.return_value = mock_cursor
        mock_db.comment_threads.find.return_value = mock_find_result

        threads = await comment_repo.get_threads_with_reported()

        assert threads == []

    def test_to_model_conversion(self, comment_repo: CommentRepo):
        """Test _to_model converts MongoDB document to CommentThread correctly."""
        doc = {
            "_id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "comment_count": 1,
            "reported_count": 0,
            "comments": [
                {
                    "id": str(uuid4()),
                    "user_id": 12345,
                    "user_name": "testuser",
                    "user_avatar_url": None,
                    "content": "Test comment",
                    "created_at": datetime.now(UTC),
                    "replies": [],
                    "reported": False,
                    "reported_by": None,
                    "reported_at": None,
                }
            ],
        }

        thread = comment_repo._to_model(doc)

        assert isinstance(thread, CommentThread)
        assert thread.id == "507f1f77bcf86cd799439011"  # _id converted to id
        assert thread.reference_type == "finding_model"
        assert thread.reference_id == "oifm_123"
        assert thread.comment_count == 1
        assert thread.reported_count == 0
        assert len(thread.comments) == 1
        assert isinstance(thread.comments[0], Comment)

    def test_to_model_preserves_original_doc(self, comment_repo: CommentRepo):
        """Test _to_model doesn't modify the original document."""
        original_doc = {
            "_id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
            "comment_count": 0,
            "reported_count": 0,
            "comments": [],
        }
        doc_copy = dict(original_doc)

        thread = comment_repo._to_model(original_doc)

        # Original document should be unchanged
        assert original_doc == doc_copy
        # But thread should have converted id
        assert thread.id == "507f1f77bcf86cd799439011"
        assert "_id" not in thread.model_dump()
