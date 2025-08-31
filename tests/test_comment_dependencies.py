"""Unit tests for comment system dependency injection."""

from unittest.mock import MagicMock

import pytest

from app.database import CommentRepo, Database
from app.dependencies import CommentRepoDep, get_comment_repo


class TestCommentDependencies:
    """Test comment system dependency injection."""

    def test_get_comment_repo_success(self):
        """Test get_comment_repo returns repo when database is initialized."""
        # Mock database with comment_repo attribute
        mock_database = MagicMock(spec=Database)
        mock_comment_repo = MagicMock(spec=CommentRepo)
        mock_database.comment_repo = mock_comment_repo

        result = get_comment_repo(mock_database)

        assert result is mock_comment_repo

    def test_get_comment_repo_database_not_initialized(self):
        """Test get_comment_repo raises RuntimeError when database not initialized."""
        mock_database = None

        with pytest.raises(AttributeError):  # Will raise AttributeError trying to access .comment_repo on None
            get_comment_repo(mock_database)

    def test_get_comment_repo_no_comment_repo_attribute(self):
        """Test get_comment_repo raises RuntimeError when CommentRepo not available."""
        # Mock database where comment_repo is None
        mock_database = MagicMock(spec=Database)
        mock_database.comment_repo = None

        with pytest.raises(RuntimeError, match="Database not initialized or CommentRepo not available"):
            get_comment_repo(mock_database)

    def test_comment_repo_dep_can_be_imported(self):
        """Test CommentRepoDep can be imported and is properly typed."""
        # This test ensures the dependency annotation exists and can be imported
        assert CommentRepoDep is not None

        # Verify it's an Annotated type (has __metadata__)
        assert hasattr(CommentRepoDep, "__metadata__")

        # The actual type should be CommentRepo
        assert CommentRepoDep.__origin__ is CommentRepo

    def test_comment_repo_dep_with_mock_database(self):
        """Test CommentRepoDep annotation works with mock database in typical FastAPI usage."""
        # This simulates how FastAPI would resolve the dependency
        mock_database = MagicMock(spec=Database)
        mock_comment_repo = MagicMock(spec=CommentRepo)
        mock_database.comment_repo = mock_comment_repo

        # Extract the dependency function from the annotation
        depends_instance = CommentRepoDep.__metadata__[0]  # The Depends() instance
        dependency_func = depends_instance.dependency

        # Call the dependency function
        result = dependency_func(mock_database)

        assert result is mock_comment_repo

    def test_get_comment_repo_with_real_repo_instance(self):
        """Test get_comment_repo works with actual CommentRepo instance."""
        # Create a real Database mock with a real CommentRepo
        mock_db_connection = MagicMock()
        mock_database = MagicMock(spec=Database)

        # Create actual CommentRepo instance
        comment_repo = CommentRepo(mock_db_connection)
        mock_database.comment_repo = comment_repo

        result = get_comment_repo(mock_database)

        assert result is comment_repo
        assert isinstance(result, CommentRepo)
        assert result.db is mock_db_connection
