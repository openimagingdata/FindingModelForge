"""Unit tests for comment system models."""

from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.models import Comment, CommentThread, UserCommentEntry


class TestUserCommentEntry:
    """Test UserCommentEntry model."""

    def test_create_user_comment_entry_with_all_fields(self):
        """Test creating UserCommentEntry with all fields."""
        created_at = datetime.now(UTC)
        entry = UserCommentEntry(
            reference_type="finding_model",
            reference_id="oifm_123",
            finding_name="Test Finding",
            comment_id="comment_123",
            created_at=created_at,
        )

        assert entry.reference_type == "finding_model"
        assert entry.reference_id == "oifm_123"
        assert entry.finding_name == "Test Finding"
        assert entry.comment_id == "comment_123"
        assert entry.created_at == created_at

    def test_create_user_comment_entry_with_draft_reference(self):
        """Test creating UserCommentEntry for draft reference."""
        created_at = datetime.now(UTC)
        entry = UserCommentEntry(
            reference_type="draft",
            reference_id="507f1f77bcf86cd799439011",
            finding_name="Draft Finding",
            comment_id="comment_456",
            created_at=created_at,
        )

        assert entry.reference_type == "draft"
        assert entry.reference_id == "507f1f77bcf86cd799439011"
        assert entry.finding_name == "Draft Finding"
        assert entry.comment_id == "comment_456"

    def test_user_comment_entry_serialization(self):
        """Test UserCommentEntry model_dump with JSON mode."""
        created_at = datetime.now(UTC)
        entry = UserCommentEntry(
            reference_type="finding_model",
            reference_id="oifm_123",
            finding_name="Test Finding",
            comment_id="comment_123",
            created_at=created_at,
        )

        data = entry.model_dump(mode="json")
        assert isinstance(data["created_at"], str)
        assert data["reference_type"] == "finding_model"
        assert data["reference_id"] == "oifm_123"


class TestComment:
    """Test Comment model."""

    @pytest.fixture
    def sample_comment_data(self):
        """Sample comment data."""
        return {
            "user_id": 12345,
            "user_name": "testuser",
            "user_avatar_url": "https://avatar.example.com/testuser.jpg",
            "content": "This is a test comment",
            "created_at": datetime.now(UTC),
        }

    def test_create_comment_with_auto_id(self, sample_comment_data):
        """Test creating Comment with auto-generated UUID."""
        comment = Comment(**sample_comment_data)

        # Check that ID is a valid UUID string
        assert isinstance(comment.id, str)
        uuid_obj = UUID(comment.id)  # Should not raise exception
        assert str(uuid_obj) == comment.id

        assert comment.user_id == 12345
        assert comment.user_name == "testuser"
        assert comment.content == "This is a test comment"
        assert comment.replies == []
        assert comment.reported is False
        assert comment.reported_by is None
        assert comment.reported_at is None

    def test_create_comment_with_custom_id(self, sample_comment_data):
        """Test creating Comment with custom ID."""
        custom_id = "custom-comment-id-123"
        comment = Comment(id=custom_id, **sample_comment_data)

        assert comment.id == custom_id
        assert comment.user_id == 12345

    def test_create_comment_with_replies(self, sample_comment_data):
        """Test creating Comment with nested replies."""
        reply_data = {
            "user_id": 67890,
            "user_name": "replyuser",
            "content": "This is a reply",
            "created_at": datetime.now(UTC),
        }
        reply = Comment(**reply_data)

        comment = Comment(replies=[reply], **sample_comment_data)

        assert len(comment.replies) == 1
        assert comment.replies[0].user_id == 67890
        assert comment.replies[0].content == "This is a reply"

    def test_comment_with_reported_fields(self, sample_comment_data):
        """Test Comment with reported fields set."""
        reported_at = datetime.now(UTC)
        comment = Comment(reported=True, reported_by=99999, reported_at=reported_at, **sample_comment_data)

        assert comment.reported is True
        assert comment.reported_by == 99999
        assert comment.reported_at == reported_at

    def test_comment_serialization(self, sample_comment_data):
        """Test Comment model_dump with JSON mode."""
        comment = Comment(**sample_comment_data)
        data = comment.model_dump(mode="json")

        assert isinstance(data["created_at"], str)
        assert data["user_id"] == 12345
        assert data["content"] == "This is a test comment"
        assert data["replies"] == []
        assert data["reported"] is False

    def test_comment_with_none_avatar(self, sample_comment_data):
        """Test Comment with None avatar_url."""
        sample_comment_data["user_avatar_url"] = None
        comment = Comment(**sample_comment_data)

        assert comment.user_avatar_url is None
        assert comment.user_name == "testuser"


class TestCommentThread:
    """Test CommentThread model."""

    @pytest.fixture
    def sample_thread_data(self):
        """Sample thread data."""
        return {
            "id": "507f1f77bcf86cd799439011",
            "reference_type": "finding_model",
            "reference_id": "oifm_123",
            "created_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }

    def test_create_comment_thread_with_defaults(self, sample_thread_data):
        """Test creating CommentThread with default values."""
        thread = CommentThread(**sample_thread_data)

        assert thread.id == "507f1f77bcf86cd799439011"
        assert thread.reference_type == "finding_model"
        assert thread.reference_id == "oifm_123"
        assert thread.comment_count == 0
        assert thread.reported_count == 0
        assert thread.comments == []

    def test_create_comment_thread_with_comments(self, sample_thread_data):
        """Test creating CommentThread with comments."""
        comment1 = Comment(
            user_id=12345,
            user_name="user1",
            content="First comment",
            created_at=datetime.now(UTC),
        )
        comment2 = Comment(
            user_id=67890,
            user_name="user2",
            content="Second comment",
            created_at=datetime.now(UTC),
        )

        thread = CommentThread(comments=[comment1, comment2], comment_count=2, **sample_thread_data)

        assert len(thread.comments) == 2
        assert thread.comment_count == 2
        assert thread.comments[0].content == "First comment"
        assert thread.comments[1].content == "Second comment"

    def test_comment_thread_with_draft_reference(self, sample_thread_data):
        """Test CommentThread with draft reference type."""
        sample_thread_data["reference_type"] = "draft"
        sample_thread_data["reference_id"] = "507f1f77bcf86cd799439012"

        thread = CommentThread(**sample_thread_data)

        assert thread.reference_type == "draft"
        assert thread.reference_id == "507f1f77bcf86cd799439012"

    def test_comment_thread_with_reported_count(self, sample_thread_data):
        """Test CommentThread with reported comments."""
        thread = CommentThread(reported_count=3, **sample_thread_data)

        assert thread.reported_count == 3

    def test_comment_thread_serialization(self, sample_thread_data):
        """Test CommentThread model_dump with JSON mode."""
        thread = CommentThread(**sample_thread_data)
        data = thread.model_dump(mode="json")

        assert isinstance(data["created_at"], str)
        assert isinstance(data["updated_at"], str)
        assert data["reference_type"] == "finding_model"
        assert data["comment_count"] == 0
        assert data["reported_count"] == 0
        assert data["comments"] == []

    def test_comment_thread_with_nested_replies(self, sample_thread_data):
        """Test CommentThread with comments that have replies."""
        reply = Comment(
            user_id=99999,
            user_name="replier",
            content="This is a reply",
            created_at=datetime.now(UTC),
        )

        main_comment = Comment(
            user_id=12345,
            user_name="main_user",
            content="Main comment",
            created_at=datetime.now(UTC),
            replies=[reply],
        )

        thread = CommentThread(
            comments=[main_comment],
            comment_count=2,  # Main comment + reply
            **sample_thread_data,
        )

        assert len(thread.comments) == 1
        assert len(thread.comments[0].replies) == 1
        assert thread.comments[0].replies[0].content == "This is a reply"
        assert thread.comment_count == 2
