"""Unit tests for draft formatting utility functions.

Tests focus on OUR code logic (dict vs model handling, None handling, field extraction),
not on testing underlying libraries like humanize or datetime.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.models import FindingModelDraft, FindingModelInputs
from app.utils.draft_formatting import (
    extract_attribute_names,
    format_date_short,
    format_draft_for_display,
    humanize_timestamp,
)


@pytest.fixture
def valid_finding_model_json(mock_finding_model) -> str:
    """Return valid FindingModelFull JSON string for testing."""
    return mock_finding_model.model_dump_json()


class TestFormatDraftForDisplay:
    """Test format_draft_for_display - our main formatting orchestration."""

    def test_dict_input_with_all_fields(self, valid_finding_model_json: str) -> None:
        """Test formatting dict input with all fields present."""
        now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        updated = datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC)
        created = datetime(2024, 10, 1, 12, 0, 0, tzinfo=UTC)

        draft_dict = {
            "id": "test-123",
            "name": "Test Finding Model",
            "status": "draft",
            "updated_at": updated,
            "created_at": created,
            "generated_json": valid_finding_model_json,
            "author_info": {"name": "Test Author", "github_username": "testuser"},
        }

        result = format_draft_for_display(draft_dict, comment_count=5, now=now)

        assert result["id"] == "test-123"
        assert result["slug"] == "test-finding-model"
        assert result["has_generated"] is True
        assert result["comment_count"] == 5
        assert result["author_name"] == "Test Author"
        assert "ago" in result["updated_display"]
        assert "2024" in result["created_at_display"]
        assert len(result["attribute_names"]) > 0

    def test_pydantic_model_input(self, valid_finding_model_json: str) -> None:
        """Test formatting Pydantic model input (not just dict)."""
        now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)

        draft_model = FindingModelDraft(
            id="test-456",
            user_id=123,
            name="Model Draft",
            status="draft",
            created_at=datetime(2024, 10, 1, 12, 0, 0, tzinfo=UTC),
            updated_at=datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC),
            inputs=FindingModelInputs(
                description="Test description",
                synonyms=["test"],
                attributes_markdown="## Test\n- test: value",
            ),
            generated_json=valid_finding_model_json,
            action_log=[],
        )

        result = format_draft_for_display(draft_model, now=now)

        assert result["id"] == "test-456"
        assert result["slug"] == "model-draft"
        assert result["has_generated"] is True
        # Verify model's enum status is handled
        assert hasattr(result["status"], "value")

    def test_missing_optional_fields(self) -> None:
        """Test our None/missing field handling."""
        draft_dict = {
            "id": "test-789",
            "name": "Minimal Draft",
            "status": "draft",
            "updated_at": datetime(2024, 10, 3, 11, 0, 0, tzinfo=UTC),
            # Missing: created_at, generated_json, author_info
        }

        result = format_draft_for_display(draft_dict)

        assert result["created_at_display"] == "N/A"
        assert result["has_generated"] is False
        assert result["author_name"] == "Unknown"
        assert result["github_username"] is None
        assert result["attribute_names"] == []

    def test_author_fallback_to_username(self) -> None:
        """Test author_name fallback logic when name is missing."""
        draft_dict = {
            "id": "test-fallback",
            "name": "Draft",
            "status": "draft",
            "updated_at": datetime(2024, 10, 3, 11, 0, 0, tzinfo=UTC),
            "author_info": {"github_username": "fallbackuser"},  # No 'name'
        }

        result = format_draft_for_display(draft_dict)

        assert result["author_name"] == "fallbackuser"

    def test_deterministic_formatting_with_now_parameter(self) -> None:
        """Test that providing 'now' makes output deterministic (for testing)."""
        draft_dict = {
            "id": "test-deterministic",
            "name": "Draft",
            "status": "draft",
            "updated_at": datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC),
        }

        fixed_now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)

        result1 = format_draft_for_display(draft_dict, now=fixed_now)
        result2 = format_draft_for_display(draft_dict, now=fixed_now)

        assert result1["updated_display"] == result2["updated_display"]


class TestExtractAttributeNames:
    """Test extract_attribute_names - our JSON parsing logic."""

    def test_valid_finding_model_json(self, valid_finding_model_json: str) -> None:
        """Test extraction from valid FindingModelFull JSON."""
        result = extract_attribute_names(valid_finding_model_json)
        assert len(result) > 0
        assert "presence" in result  # From abdominal_abscess.fm.json

    def test_none_input(self) -> None:
        """Test our None handling."""
        assert extract_attribute_names(None) == []

    def test_invalid_json(self) -> None:
        """Test our error handling for invalid JSON."""
        assert extract_attribute_names("not valid json {") == []
        assert extract_attribute_names("") == []

    def test_missing_attributes_key(self) -> None:
        """Test handling when attributes field is missing."""
        json_str = '{"name": "Test Model"}'
        assert extract_attribute_names(json_str) == []


class TestHumanizeTimestamp:
    """Test humanize_timestamp - our wrapper around humanize library."""

    def test_none_handling(self) -> None:
        """Test our None input handling."""
        assert humanize_timestamp(None) == "Unknown"

    def test_invalid_input_handling(self) -> None:
        """Test our error handling for invalid inputs."""
        assert humanize_timestamp("invalid") == "Unknown"
        assert humanize_timestamp(12345) == "Unknown"  # type: ignore[arg-type]

    def test_timezone_naive_datetime_handling(self) -> None:
        """Test that we add UTC timezone to naive datetimes."""
        now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        past_naive = datetime(2024, 10, 3, 10, 0, 0)  # No timezone

        result = humanize_timestamp(past_naive, now=now)
        assert "ago" in result  # Should work correctly

    def test_iso_string_parsing(self) -> None:
        """Test that we parse ISO strings (for cache compatibility)."""
        now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        iso_string = "2024-10-03T10:00:00Z"

        result = humanize_timestamp(iso_string, now=now)
        assert "ago" in result

    def test_deterministic_with_now_parameter(self) -> None:
        """Test deterministic output with 'now' parameter."""
        past = datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC)
        fixed_now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)

        result1 = humanize_timestamp(past, now=fixed_now)
        result2 = humanize_timestamp(past, now=fixed_now)

        assert result1 == result2


class TestFormatDateShort:
    """Test format_date_short - our date formatting wrapper."""

    def test_none_handling(self) -> None:
        """Test our None input handling."""
        assert format_date_short(None) == "N/A"

    def test_invalid_input_handling(self) -> None:
        """Test our error handling for invalid inputs."""
        assert format_date_short("invalid") == "N/A"
        assert format_date_short(12345) == "N/A"  # type: ignore[arg-type]

    def test_timezone_naive_datetime_handling(self) -> None:
        """Test that we add UTC timezone to naive datetimes."""
        dt_naive = datetime(2024, 12, 25, 12, 0, 0)
        result = format_date_short(dt_naive)
        assert "2024" in result  # Should work correctly

    def test_iso_string_parsing(self) -> None:
        """Test that we parse ISO strings (for cache compatibility)."""
        iso_string = "2024-07-04T10:00:00Z"
        result = format_date_short(iso_string)
        assert "2024" in result

    def test_correct_format(self) -> None:
        """Test that output format is correct."""
        dt = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)
        assert format_date_short(dt) == "Oct 03, 2024"


class TestIntegration:
    """Integration tests showing all functions work together correctly."""

    def test_complete_draft_formatting_workflow(self, valid_finding_model_json: str) -> None:
        """Test complete workflow from raw draft data to formatted display."""
        now = datetime(2024, 10, 3, 12, 0, 0, tzinfo=UTC)

        raw_draft = {
            "id": "integration-test",
            "name": "Complete Test Draft",
            "status": "submitted",
            "updated_at": datetime(2024, 10, 3, 8, 0, 0, tzinfo=UTC),
            "created_at": datetime(2024, 10, 1, 10, 0, 0, tzinfo=UTC),
            "generated_json": valid_finding_model_json,
            "author_info": {"name": "Integration Tester", "github_username": "inttest"},
        }

        result = format_draft_for_display(raw_draft, comment_count=10, now=now)

        # All components work together
        assert result["slug"] == "complete-test-draft"
        assert result["has_generated"] is True
        assert result["comment_count"] == 10
        assert result["author_name"] == "Integration Tester"
        assert len(result["attribute_names"]) > 0
        assert "ago" in result["updated_display"]
        assert "2024" in result["created_at_display"]

    def test_edge_case_handling_consistency(self) -> None:
        """Test that edge cases don't crash and return sensible defaults."""
        edge_case_draft = {
            "id": "edge-case",
            "name": "",
            "status": "draft",
            "updated_at": None,
            "created_at": None,
            "generated_json": "invalid json {",
        }

        result = format_draft_for_display(edge_case_draft)

        # Should handle gracefully with defaults
        assert result["slug"] == ""
        assert result["updated_display"] == "Unknown"
        assert result["created_at_display"] == "N/A"
        assert result["attribute_names"] == []
        assert result["author_name"] == "Unknown"

    def test_output_keys_match_expected_format(self) -> None:
        """Test that output has all expected keys for backward compatibility."""
        draft = {
            "id": "test",
            "name": "Test",
            "status": "draft",
            "updated_at": datetime(2024, 10, 3, 10, 0, 0, tzinfo=UTC),
        }

        result = format_draft_for_display(draft)

        expected_keys = {
            "id",
            "name",
            "status",
            "updated_at",
            "updated_display",
            "created_at",
            "created_at_display",
            "slug",
            "has_generated",
            "comment_count",
            "attribute_names",
            "author_name",
            "github_username",
        }

        assert set(result.keys()) == expected_keys
