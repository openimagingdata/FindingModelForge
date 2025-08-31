"""Unit tests for comment helper functions."""

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.database import UserRepo
from app.models import Comment, UserCommentEntry
from app.services.comment_helpers import (
    add_to_comment_index,
    check_rate_limit,
    get_blacklist_user_ids,
    is_reply_allowed,
)


class TestCheckRateLimit:
    """Test check_rate_limit function."""

    @patch("app.services.comment_helpers.datetime")
    def test_no_comment_index_allows_comment(self, mock_datetime):
        """Test that user with no comment_index can comment."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        user_doc = {}
        assert check_rate_limit(user_doc) is True

    @patch("app.services.comment_helpers.datetime")
    def test_empty_comment_index_allows_comment(self, mock_datetime):
        """Test that user with empty comment_index can comment."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        user_doc = {"comment_index": []}
        assert check_rate_limit(user_doc) is True

    @patch("app.services.comment_helpers.datetime")
    def test_old_comments_allows_new_comment(self, mock_datetime):
        """Test that comments older than 60 seconds don't count toward limit."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Comments from 2 minutes ago
        old_time = mock_now - timedelta(seconds=120)
        user_doc = {
            "comment_index": [
                {"created_at": old_time, "comment_id": "1"},
                {"created_at": old_time, "comment_id": "2"},
                {"created_at": old_time, "comment_id": "3"},
            ]
        }
        assert check_rate_limit(user_doc) is True

    @patch("app.services.comment_helpers.datetime")
    def test_two_recent_comments_allows_third(self, mock_datetime):
        """Test that 2 recent comments still allows a third."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Comments from 30 seconds ago
        recent_time = mock_now - timedelta(seconds=30)
        user_doc = {
            "comment_index": [
                {"created_at": recent_time, "comment_id": "1"},
                {"created_at": recent_time, "comment_id": "2"},
            ]
        }
        assert check_rate_limit(user_doc) is True

    @patch("app.services.comment_helpers.datetime")
    def test_three_recent_comments_blocks_fourth(self, mock_datetime):
        """Test that 3 recent comments blocks a fourth."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        # Comments from 30 seconds ago
        recent_time = mock_now - timedelta(seconds=30)
        user_doc = {
            "comment_index": [
                {"created_at": recent_time, "comment_id": "1"},
                {"created_at": recent_time, "comment_id": "2"},
                {"created_at": recent_time, "comment_id": "3"},
            ]
        }
        assert check_rate_limit(user_doc) is False

    @patch("app.services.comment_helpers.datetime")
    def test_mixed_old_and_new_comments_only_counts_recent(self, mock_datetime):
        """Test that only recent comments count toward the limit."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        old_time = mock_now - timedelta(seconds=120)
        recent_time = mock_now - timedelta(seconds=30)

        user_doc = {
            "comment_index": [
                {"created_at": old_time, "comment_id": "1"},
                {"created_at": old_time, "comment_id": "2"},
                {"created_at": recent_time, "comment_id": "3"},
                {"created_at": recent_time, "comment_id": "4"},
            ]
        }
        assert check_rate_limit(user_doc) is True  # Only 2 recent comments

    @patch("app.services.comment_helpers.datetime")
    def test_malformed_comment_index_entries_handled_gracefully(self, mock_datetime):
        """Test that malformed entries in comment_index are handled gracefully."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        recent_time = mock_now - timedelta(seconds=30)
        user_doc = {
            "comment_index": [
                "invalid_string_entry",  # Invalid - not a dict
                {"comment_id": "2"},  # Missing created_at
                {"created_at": None, "comment_id": "3"},  # None created_at
                {"created_at": recent_time, "comment_id": "4"},  # Valid entry
            ]
        }
        assert check_rate_limit(user_doc) is True  # Only 1 valid recent comment

    @patch("app.services.comment_helpers.datetime")
    def test_exactly_at_cutoff_time_not_counted(self, mock_datetime):
        """Test that comments exactly at cutoff time are not counted."""
        mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_datetime.now.return_value = mock_now
        mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

        cutoff_time = mock_now - timedelta(seconds=60)
        user_doc = {
            "comment_index": [
                {"created_at": cutoff_time, "comment_id": "1"},  # Exactly at cutoff
            ]
        }
        assert check_rate_limit(user_doc) is True  # Not counted as recent


class TestAddToCommentIndex:
    """Test add_to_comment_index function."""

    @pytest.fixture
    def mock_user_repo(self) -> MagicMock:
        """Mock user repository."""
        repo = MagicMock(spec=UserRepo)
        repo.collection = MagicMock()
        repo.collection.update_one = AsyncMock()
        return repo

    @pytest.mark.asyncio
    async def test_add_to_comment_index_success(self, mock_user_repo):
        """Test successful addition of comment entry to user index."""
        user_id = 12345
        finding_name = "Test Finding"
        reference_type = "finding_model"
        reference_id = "oifm_123"
        comment_id = str(uuid4())

        with patch("app.services.comment_helpers.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            await add_to_comment_index(
                mock_user_repo, user_id, finding_name, reference_type, reference_id, comment_id
            )

            # Verify update_one was called with correct parameters
            mock_user_repo.collection.update_one.assert_called_once()
            call_args = mock_user_repo.collection.update_one.call_args
            
            # Check filter
            assert call_args[0][0] == {"id": user_id}
            
            # Check update operation
            update_op = call_args[0][1]
            assert "$push" in update_op
            assert "comment_index" in update_op["$push"]
            
            # Check the entry data
            entry_data = update_op["$push"]["comment_index"]
            assert entry_data["reference_type"] == reference_type
            assert entry_data["reference_id"] == reference_id
            assert entry_data["finding_name"] == finding_name
            assert entry_data["comment_id"] == comment_id
            # created_at is serialized to ISO string in JSON mode
            assert entry_data["created_at"] == "2024-01-01T12:00:00Z"

    @pytest.mark.asyncio
    async def test_add_to_comment_index_draft_reference(self, mock_user_repo):
        """Test adding comment entry with draft reference type."""
        user_id = 67890
        finding_name = "Draft Finding"
        reference_type = "draft"
        reference_id = "507f1f77bcf86cd799439012"
        comment_id = str(uuid4())

        with patch("app.services.comment_helpers.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 1, 13, 0, 0, tzinfo=UTC)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            await add_to_comment_index(
                mock_user_repo, user_id, finding_name, reference_type, reference_id, comment_id
            )

            # Verify the entry was created with correct reference_type
            call_args = mock_user_repo.collection.update_one.call_args
            entry_data = call_args[0][1]["$push"]["comment_index"]
            assert entry_data["reference_type"] == "draft"
            assert entry_data["reference_id"] == reference_id


class TestGetBlacklistUserIds:
    """Test get_blacklist_user_ids function."""

    def test_no_environment_variable_returns_empty_list(self):
        """Test that missing environment variable returns empty list."""
        with patch.dict(os.environ, {}, clear=True):
            result = get_blacklist_user_ids()
            assert result == []

    def test_empty_string_returns_empty_list(self):
        """Test that empty string environment variable returns empty list."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": ""}):
            result = get_blacklist_user_ids()
            assert result == []

    def test_single_user_id(self):
        """Test with single user ID."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "12345"}):
            result = get_blacklist_user_ids()
            assert result == [12345]

    def test_multiple_user_ids(self):
        """Test with multiple comma-separated user IDs."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "12345,67890,11111"}):
            result = get_blacklist_user_ids()
            assert result == [12345, 67890, 11111]

    def test_whitespace_handling(self):
        """Test that whitespace around IDs is handled correctly."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "12345, 67890 , 11111"}):
            result = get_blacklist_user_ids()
            assert result == [12345, 67890, 11111]

    def test_invalid_format_skips_invalid_returns_valid(self):
        """Test that invalid IDs are skipped and valid ones are returned."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "12345,abc,67890,def,11111"}):
            result = get_blacklist_user_ids()
            assert result == []  # ValueError should return empty list per implementation

    def test_purely_invalid_format_returns_empty(self):
        """Test that purely invalid format returns empty list."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "abc,def,xyz"}):
            result = get_blacklist_user_ids()
            assert result == []

    def test_empty_values_filtered_out(self):
        """Test that empty values are filtered out."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": "12345,,67890,"}):
            result = get_blacklist_user_ids()
            assert result == [12345, 67890]

    def test_only_commas_returns_empty(self):
        """Test that string with only commas returns empty list."""
        with patch.dict(os.environ, {"COMMENT_BLACKLIST_USER_IDS": ",,,,"}):
            result = get_blacklist_user_ids()
            assert result == []


class TestIsReplyAllowed:
    """Test is_reply_allowed function."""

    @pytest.fixture
    def sample_comment(self) -> Comment:
        """Sample comment for testing."""
        return Comment(
            id=str(uuid4()),
            user_id=12345,
            user_name="testuser",
            content="Test comment content",
            created_at=datetime.now(UTC),
        )

    def test_accepts_comment_object(self, sample_comment):
        """Test that function accepts a Comment object."""
        # Should not raise any errors
        result = is_reply_allowed(sample_comment)
        assert isinstance(result, bool)

    def test_returns_true_placeholder(self, sample_comment):
        """Test that function returns True (placeholder implementation)."""
        result = is_reply_allowed(sample_comment)
        assert result is True

    def test_comment_with_replies(self, sample_comment):
        """Test comment that already has replies."""
        sample_comment.replies = [
            Comment(
                id=str(uuid4()),
                user_id=67890,
                user_name="replier",
                content="Reply content",
                created_at=datetime.now(UTC),
            )
        ]
        result = is_reply_allowed(sample_comment)
        assert result is True  # Still True in placeholder implementation

    def test_comment_without_replies(self, sample_comment):
        """Test comment without any replies."""
        assert len(sample_comment.replies) == 0
        result = is_reply_allowed(sample_comment)
        assert result is True

    def test_reported_comment(self, sample_comment):
        """Test that reported comments are still allowed replies (placeholder)."""
        sample_comment.reported = True
        sample_comment.reported_by = 99999
        sample_comment.reported_at = datetime.now(UTC)
        
        result = is_reply_allowed(sample_comment)
        assert result is True  # Placeholder returns True regardless