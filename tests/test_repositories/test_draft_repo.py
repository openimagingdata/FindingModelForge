"""Unit tests for DraftRepo iteration methods."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from bson import ObjectId

from app.database import DraftRepo
from app.models import FindingModelDraft, FindingModelInputs


class TestDraftRepoIterationMethods:
    """Test iteration-specific methods in DraftRepo."""

    @pytest.fixture
    def mock_collection(self) -> MagicMock:
        """Create a mock MongoDB collection."""
        collection = MagicMock()
        collection.find_one = AsyncMock()
        collection.update_one = AsyncMock()
        return collection

    @pytest.fixture
    def mock_db(self, mock_collection: MagicMock) -> MagicMock:
        """Create a mock database."""
        db = MagicMock()
        db.finding_model_drafts = mock_collection
        return db

    @pytest.fixture
    def draft_repo(self, mock_db: MagicMock) -> DraftRepo:
        """Create DraftRepo instance with mocked database."""
        return DraftRepo(mock_db)

    @pytest.mark.asyncio
    async def test_get_iteration_draft_returns_existing(
        self, draft_repo: DraftRepo, mock_collection: MagicMock
    ) -> None:
        """Test get_iteration_draft returns existing iteration draft."""
        # Arrange
        user_id = 123
        base_model_id = "oifm:test-model"
        now = datetime.now(UTC)

        mock_doc = {
            "_id": ObjectId(),
            "user_id": user_id,
            "base_model_id": base_model_id,
            "is_iteration": True,
            "status": "draft",
            "name": "Test Finding",
            "created_at": now,
            "updated_at": now,
            "inputs": {
                "description": "Test description",
                "synonyms": [],
                "attributes_markdown": "",
            },
            "generated_json": '{"test": "data"}',
            "action_log": [],
        }

        mock_collection.find_one.return_value = mock_doc

        # Act
        result = await draft_repo.get_iteration_draft(user_id, base_model_id)

        # Assert
        assert result is not None
        assert isinstance(result, FindingModelDraft)
        assert result.user_id == user_id
        assert result.base_model_id == base_model_id
        assert result.is_iteration is True
        assert result.status == "draft"

        # Verify query was correct
        mock_collection.find_one.assert_called_once_with(
            {
                "user_id": user_id,
                "base_model_id": base_model_id,
                "is_iteration": True,
                "status": "draft",
            }
        )

    @pytest.mark.asyncio
    async def test_get_iteration_draft_returns_none_when_not_found(
        self, draft_repo: DraftRepo, mock_collection: MagicMock
    ) -> None:
        """Test get_iteration_draft returns None when no draft exists."""
        # Arrange
        user_id = 123
        base_model_id = "oifm:nonexistent"
        mock_collection.find_one.return_value = None

        # Act
        result = await draft_repo.get_iteration_draft(user_id, base_model_id)

        # Assert
        assert result is None
        mock_collection.find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_draft_with_iteration_fields(self, draft_repo: DraftRepo, mock_collection: MagicMock) -> None:
        """Test save_draft accepts and uses iteration fields."""
        # Arrange
        user_id = 123
        base_model_id = "oifm:test-model"
        name = "Test Finding"
        inputs = FindingModelInputs(
            description="Test description",
            synonyms=[],
            attributes_markdown="",
        )

        # Mock the upsert response
        mock_upserted_id = ObjectId()
        mock_collection.update_one.return_value = MagicMock(upserted_id=mock_upserted_id, matched_count=0)

        # Mock find_one for _load_by_oid
        now = datetime.now(UTC)
        mock_doc = {
            "_id": mock_upserted_id,
            "user_id": user_id,
            "name": name,
            "base_model_id": base_model_id,
            "is_iteration": True,
            "status": "draft",
            "created_at": now,
            "updated_at": now,
            "inputs": inputs.model_dump(),
            "generated_json": None,
            "action_log": [],
        }
        mock_collection.find_one.return_value = mock_doc

        # Act
        result = await draft_repo.save_draft(
            user_id=user_id,
            name=name,
            inputs=inputs,
            is_iteration=True,
            base_model_id=base_model_id,
        )

        # Assert
        assert result is not None
        assert result.is_iteration is True
        assert result.base_model_id == base_model_id

        # Verify the upsert query used iteration-specific filter
        calls = mock_collection.update_one.call_args_list
        assert len(calls) >= 1
        first_call = calls[0]
        filter_doc = first_call[0][0]
        assert filter_doc["user_id"] == user_id
        assert filter_doc["base_model_id"] == base_model_id
        assert filter_doc["is_iteration"] is True
        assert filter_doc["status"] == "draft"

    @pytest.mark.asyncio
    async def test_update_generated_json_success(self, draft_repo: DraftRepo, mock_collection: MagicMock) -> None:
        """Test update_generated_json successfully updates the draft."""
        # Arrange
        draft_id = str(ObjectId())
        user_id = 123
        new_json = '{"updated": "content"}'

        mock_result = MagicMock()
        mock_result.matched_count = 1
        mock_collection.update_one.return_value = mock_result

        # Act
        success = await draft_repo.update_generated_json(draft_id, user_id, new_json)

        # Assert
        assert success is True

        # Verify the update query
        mock_collection.update_one.assert_called_once()
        call_args = mock_collection.update_one.call_args
        filter_doc = call_args[0][0]
        update_doc = call_args[0][1]

        assert filter_doc["_id"] == ObjectId(draft_id)
        assert filter_doc["user_id"] == user_id
        assert update_doc["$set"]["generated_json"] == new_json
        assert "updated_at" in update_doc["$set"]

    @pytest.mark.asyncio
    async def test_update_generated_json_returns_false_when_not_found(
        self, draft_repo: DraftRepo, mock_collection: MagicMock
    ) -> None:
        """Test update_generated_json returns False when draft not found."""
        # Arrange
        draft_id = str(ObjectId())
        user_id = 123
        new_json = '{"updated": "content"}'

        mock_result = MagicMock()
        mock_result.matched_count = 0
        mock_collection.update_one.return_value = mock_result

        # Act
        success = await draft_repo.update_generated_json(draft_id, user_id, new_json)

        # Assert
        assert success is False

    @pytest.mark.asyncio
    async def test_update_generated_json_returns_false_for_invalid_id(
        self, draft_repo: DraftRepo, mock_collection: MagicMock
    ) -> None:
        """Test update_generated_json returns False for invalid ObjectId."""
        # Arrange
        draft_id = "not-a-valid-objectid"
        user_id = 123
        new_json = '{"updated": "content"}'

        # Act
        success = await draft_repo.update_generated_json(draft_id, user_id, new_json)

        # Assert
        assert success is False
        mock_collection.update_one.assert_not_called()
