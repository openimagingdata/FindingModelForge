"""Test iteration fields for FindingModelDraft model.

Tests for Sprint 1, Phase 1: Data Model changes for model iteration feature.
"""

from datetime import UTC, datetime

import pytest

from app.models import DraftStatus, FindingModelDraft, FindingModelInputs


class TestFindingModelDraftIterationFields:
    """Test iteration fields in FindingModelDraft model."""

    @pytest.fixture
    def sample_inputs(self) -> FindingModelInputs:
        """Sample inputs for draft creation."""
        return FindingModelInputs(
            description="Test finding description for iteration testing",
            synonyms=["test", "finding"],
            attributes_markdown="## Attributes\n\n### presence\nWhether present",
        )

    def test_finding_model_draft_defaults(self, sample_inputs: FindingModelInputs) -> None:
        """Test that new iteration fields have proper defaults."""
        draft = FindingModelDraft(
            id="test-draft-id",
            user_id=123,
            name="Test Draft",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=sample_inputs,
        )

        # Verify defaults
        assert draft.is_iteration is False
        assert draft.base_model_id is None

    def test_finding_model_draft_serialization_with_iteration_fields(self, sample_inputs: FindingModelInputs) -> None:
        """Test serialization round-trip with iteration fields."""
        created_at = datetime.now(UTC)
        updated_at = datetime.now(UTC)

        # Create draft with iteration fields set
        original_draft = FindingModelDraft(
            id="test-draft-iteration",
            user_id=456,
            author_username="testuser",
            author_name="Test User",
            name="Iterated Finding",
            created_at=created_at,
            updated_at=updated_at,
            inputs=sample_inputs,
            generated_json='{"test": "json"}',
            status=DraftStatus.DRAFT,
            action_log=[],
            is_iteration=True,
            base_model_id="oifm_base_model_123",
        )

        # Serialize to JSON
        json_data = original_draft.model_dump_json()

        # Verify JSON contains iteration fields
        assert "is_iteration" in json_data
        assert "base_model_id" in json_data
        assert '"is_iteration":true' in json_data or '"is_iteration": true' in json_data
        assert "oifm_base_model_123" in json_data

        # Deserialize back to model
        restored_draft = FindingModelDraft.model_validate_json(json_data)

        # Verify all fields match, including iteration fields
        assert restored_draft.id == original_draft.id
        assert restored_draft.user_id == original_draft.user_id
        assert restored_draft.name == original_draft.name
        assert restored_draft.is_iteration == original_draft.is_iteration
        assert restored_draft.base_model_id == original_draft.base_model_id

    def test_finding_model_draft_defaults_for_existing_drafts(self, sample_inputs: FindingModelInputs) -> None:
        """Test that existing drafts without iteration fields work correctly."""
        # Simulate JSON from database that doesn't have the new fields
        # (i.e., drafts created before the iteration feature was added)
        draft_json_without_iteration_fields = """{
            "id": "old-draft-id",
            "user_id": 789,
            "author_username": "olduser",
            "author_name": "Old User",
            "name": "Old Draft",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T12:00:00Z",
            "inputs": {
                "description": "Old draft description for backward compatibility testing",
                "synonyms": ["old", "draft"],
                "attributes_markdown": "## Attributes\\n\\n### presence\\nValue"
            },
            "generated_json": null,
            "status": "draft",
            "action_log": []
        }"""

        # Should deserialize successfully with defaults
        draft = FindingModelDraft.model_validate_json(draft_json_without_iteration_fields)

        # Verify the draft loaded correctly
        assert draft.id == "old-draft-id"
        assert draft.user_id == 789
        assert draft.name == "Old Draft"

        # Verify iteration fields have defaults
        assert draft.is_iteration is False
        assert draft.base_model_id is None

    def test_finding_model_draft_creation_workflow_defaults(self, sample_inputs: FindingModelInputs) -> None:
        """Test that normal creation workflow (non-iteration) has correct defaults."""
        # Simulate a draft created through the normal creation workflow
        creation_draft = FindingModelDraft(
            id="creation-draft-id",
            user_id=111,
            name="New Finding",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=sample_inputs,
            status=DraftStatus.DRAFT,
        )

        # Should have iteration=False and base_model_id=None
        assert creation_draft.is_iteration is False
        assert creation_draft.base_model_id is None

    def test_finding_model_draft_iteration_workflow(self, sample_inputs: FindingModelInputs) -> None:
        """Test that iteration workflow sets fields correctly."""
        # Simulate a draft created through the iteration workflow
        iteration_draft = FindingModelDraft(
            id="iteration-draft-id",
            user_id=222,
            name="Iterated Finding v2",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=sample_inputs,
            status=DraftStatus.DRAFT,
            is_iteration=True,
            base_model_id="oifm_original_model_456",
        )

        # Should have iteration fields set
        assert iteration_draft.is_iteration is True
        assert iteration_draft.base_model_id == "oifm_original_model_456"

    def test_finding_model_draft_model_dump_includes_iteration_fields(self, sample_inputs: FindingModelInputs) -> None:
        """Test that model_dump includes iteration fields in output."""
        draft = FindingModelDraft(
            id="test-dump",
            user_id=333,
            name="Test Dump",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=sample_inputs,
            is_iteration=True,
            base_model_id="oifm_test_base",
        )

        # Get dict representation
        draft_dict = draft.model_dump()

        # Verify iteration fields are in dict
        assert "is_iteration" in draft_dict
        assert "base_model_id" in draft_dict
        assert draft_dict["is_iteration"] is True
        assert draft_dict["base_model_id"] == "oifm_test_base"

    def test_finding_model_draft_model_dump_json_mode(self, sample_inputs: FindingModelInputs) -> None:
        """Test that model_dump with json mode handles iteration fields correctly."""
        draft = FindingModelDraft(
            id="test-json-mode",
            user_id=444,
            name="JSON Mode Test",
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            inputs=sample_inputs,
            is_iteration=True,
            base_model_id="oifm_json_test",
        )

        # Get dict with JSON mode (for MongoDB serialization)
        draft_dict = draft.model_dump(mode="json")

        # Verify iteration fields are properly serialized
        assert draft_dict["is_iteration"] is True
        assert draft_dict["base_model_id"] == "oifm_json_test"

        # Verify datetime fields are serialized as strings (JSON mode)
        assert isinstance(draft_dict["created_at"], str)
        assert isinstance(draft_dict["updated_at"], str)
