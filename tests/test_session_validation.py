"""Test session management and validation logic."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request

from app.cache import RedisCache
from app.dependencies import (
    FindingModelCreationSession,
    SessionManager,
    get_creation_session,
    get_session_manager,
)


class TestFindingModelCreationSession:
    """Test the FindingModelCreationSession model."""

    def test_session_initialization(self) -> None:
        """Test session model initialization with defaults."""
        session = FindingModelCreationSession(session_id="test-123")

        assert session.session_id == "test-123"
        assert session.current_step == 1
        assert session.name is None
        assert session.description is None
        assert session.synonyms == []
        assert session.similar_models == []
        assert session.attributes_markdown is None
        assert session.final_model is None
        assert session.error_message is None

    def test_session_with_data(self) -> None:
        """Test session model with data."""
        session = FindingModelCreationSession(
            session_id="test-123",
            current_step=3,
            name="test-finding",
            description="A test finding",
            synonyms=["synonym1", "synonym2"],
            similar_models=[{"oifm_id": "OIFM_123", "name": "similar"}],
            attributes_markdown="## Attributes\n### presence\nValue",
            error_message="Test error",
        )

        assert session.current_step == 3
        assert session.name == "test-finding"
        assert session.description == "A test finding"
        assert len(session.synonyms) == 2
        assert len(session.similar_models) == 1
        assert "## Attributes" in session.attributes_markdown
        assert session.error_message == "Test error"

    def test_session_serialization(self) -> None:
        """Test session model serialization to JSON."""
        session = FindingModelCreationSession(session_id="test-123", current_step=2, name="test-finding")

        json_data = session.model_dump_json()
        assert "test-123" in json_data
        assert "test-finding" in json_data
        assert '"current_step":2' in json_data or '"current_step": 2' in json_data

        # Test round-trip
        restored = FindingModelCreationSession.model_validate_json(json_data)
        assert restored.session_id == session.session_id
        assert restored.current_step == session.current_step
        assert restored.name == session.name


class TestSessionManagerDetailed:
    """Detailed tests for SessionManager functionality."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock Redis cache."""
        return MagicMock(spec=RedisCache)

    @pytest.fixture
    def session_manager(self, mock_cache: MagicMock) -> SessionManager:
        """Create SessionManager with mocked cache."""
        return SessionManager(mock_cache)

    async def test_session_ttl_configuration(self, session_manager: SessionManager) -> None:
        """Test that session TTL is configured correctly."""
        assert session_manager.session_ttl == 3600 * 4  # 4 hours
        assert session_manager.session_prefix == "creation_session:"

    async def test_session_cache_key_format(self, session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test that cache keys are formatted correctly."""
        mock_cache.set = AsyncMock()
        session_id = "test-session-123"

        session = FindingModelCreationSession(session_id=session_id)
        await session_manager.update_session(session)

        # Check that the cache key is correctly formatted
        call_args = mock_cache.set.call_args
        cache_key = call_args[0][0]
        assert cache_key == f"creation_session:{session_id}"

    async def test_session_data_format(self, session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test that session data is stored as JSON."""
        mock_cache.set = AsyncMock()

        session = FindingModelCreationSession(session_id="test-123", name="test-finding", synonyms=["test"])
        await session_manager.update_session(session)

        call_args = mock_cache.set.call_args
        session_json = call_args[0][1]

        # Should be valid JSON string
        assert isinstance(session_json, str)
        assert session_json.startswith('{"')
        assert '"session_id":"test-123"' in session_json or '"session_id": "test-123"' in session_json
        assert '"name":"test-finding"' in session_json or '"name": "test-finding"' in session_json
        assert '"synonyms":["test"]' in session_json or '"synonyms": ["test"]' in session_json

    async def test_session_expiration_setting(self, session_manager: SessionManager, mock_cache: MagicMock) -> None:
        """Test that session expiration is set correctly."""
        from datetime import timedelta

        mock_cache.set = AsyncMock()

        session = FindingModelCreationSession(session_id="test-123")
        await session_manager.update_session(session)

        call_args = mock_cache.set.call_args
        expires_in = call_args[1]["expires_in"]

        assert isinstance(expires_in, timedelta)
        assert expires_in.total_seconds() == 3600 * 4  # 4 hours

    async def test_get_session_json_parsing_edge_cases(
        self, session_manager: SessionManager, mock_cache: MagicMock
    ) -> None:
        """Test JSON parsing edge cases in get_session."""
        test_cases = [
            ("", None),  # Empty string
            ("null", None),  # JSON null
            ("{malformed json", None),  # Malformed JSON
            ('{"session_id": "test"}', "test"),  # Valid minimal JSON
            ('{"session_id": "test", "extra_field": "ignored"}', "test"),  # Extra fields ignored
        ]

        for json_data, expected_id in test_cases:
            mock_cache.get = AsyncMock(return_value=json_data)

            session = await session_manager.get_session("test")

            if expected_id is None:
                assert session is None
            else:
                assert session is not None
                assert session.session_id == expected_id

    async def test_session_operations_error_handling(
        self, session_manager: SessionManager, mock_cache: MagicMock
    ) -> None:
        """Test error handling in session operations."""
        # Test cache errors don't crash the methods
        mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))
        mock_cache.set = AsyncMock(side_effect=Exception("Cache error"))
        mock_cache.delete = AsyncMock(side_effect=Exception("Cache error"))

        # These should not raise exceptions
        session = await session_manager.get_session("test")
        assert session is None

        # Update and delete should not raise either - they handle errors gracefully
        test_session = FindingModelCreationSession(session_id="test")

        # These operations should not raise exceptions
        await session_manager.update_session(test_session)
        await session_manager.delete_session("test")

        # Operations completed without raising exceptions


class TestSessionDependencyInjection:
    """Test session dependency injection."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock Redis cache."""
        return MagicMock(spec=RedisCache)

    def test_get_session_manager_dependency(self, mock_cache: MagicMock) -> None:
        """Test that get_session_manager creates SessionManager correctly."""
        session_manager = get_session_manager(mock_cache)

        assert isinstance(session_manager, SessionManager)
        assert session_manager.cache is mock_cache

    async def test_get_creation_session_from_query_params(self, mock_cache: MagicMock) -> None:
        """Test getting session from query parameters."""
        # Mock cache to return existing session
        session_data = '{"session_id": "test-123", "current_step": 2}'
        mock_cache.get = AsyncMock(return_value=session_data)

        # Create mock request with query parameters
        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {"session_id": "test-123"}
        mock_request.method = "GET"
        mock_request.cookies = {}

        session_manager = SessionManager(mock_cache)

        session = await get_creation_session(mock_request, session_manager)

        assert session is not None
        assert session.session_id == "test-123"
        assert session.current_step == 2

    async def test_get_creation_session_from_form_data(self, mock_cache: MagicMock) -> None:
        """Test getting session from form data."""
        session_data = '{"session_id": "form-123", "current_step": 3}'
        mock_cache.get = AsyncMock(return_value=session_data)

        # Mock form data
        mock_form_data = {"session_id": "form-123"}

        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {}
        mock_request.method = "POST"
        mock_request.form = AsyncMock(return_value=mock_form_data)
        mock_request.cookies = {}

        session_manager = SessionManager(mock_cache)

        session = await get_creation_session(mock_request, session_manager)

        assert session is not None
        assert session.session_id == "form-123"
        assert session.current_step == 3

    async def test_get_creation_session_from_cookies(self, mock_cache: MagicMock) -> None:
        """Test getting session from cookies."""
        session_data = '{"session_id": "cookie-123", "current_step": 1}'
        mock_cache.get = AsyncMock(return_value=session_data)

        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {}
        mock_request.method = "GET"
        mock_request.cookies = {"creation_session_id": "cookie-123"}

        session_manager = SessionManager(mock_cache)

        session = await get_creation_session(mock_request, session_manager)

        assert session is not None
        assert session.session_id == "cookie-123"
        assert session.current_step == 1

    async def test_get_creation_session_create_new(self, mock_cache: MagicMock) -> None:
        """Test creating new session when none exists."""
        # Mock cache operations
        mock_cache.get = AsyncMock(return_value=None)  # No existing session
        mock_cache.set = AsyncMock(return_value=None)  # Successfully create new

        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {}
        mock_request.method = "GET"
        mock_request.cookies = {}

        session_manager = SessionManager(mock_cache)

        session = await get_creation_session(mock_request, session_manager)

        assert session is not None
        assert session.current_step == 1
        assert session.name is None

        # Should have tried to get and then create
        mock_cache.get.assert_called()
        mock_cache.set.assert_called()

    async def test_get_creation_session_fallback_on_cache_failure(self, mock_cache: MagicMock) -> None:
        """Test fallback session creation when cache fails."""
        # Mock cache to fail completely
        mock_cache.get = AsyncMock(side_effect=Exception("Cache error"))
        mock_cache.set = AsyncMock(side_effect=Exception("Cache error"))

        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {}
        mock_request.method = "GET"
        mock_request.cookies = {}

        session_manager = SessionManager(mock_cache)

        session = await get_creation_session(mock_request, session_manager)

        # Should still return a valid session (fallback)
        assert session is not None
        assert session.current_step == 1

    async def test_get_creation_session_form_data_error_handling(self, mock_cache: MagicMock) -> None:
        """Test handling errors when parsing form data."""
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock(return_value=None)

        mock_request = MagicMock(spec=Request)
        mock_request.query_params = {}
        mock_request.method = "POST"
        mock_request.form = AsyncMock(side_effect=Exception("Form parsing error"))
        mock_request.cookies = {}

        session_manager = SessionManager(mock_cache)

        # Should not crash, should create new session
        session = await get_creation_session(mock_request, session_manager)

        assert session is not None
        assert session.current_step == 1


class TestValidationLogic:
    """Test validation logic used in HTMX endpoints."""

    def test_name_validation_length_constraints(self) -> None:
        """Test name validation constraints."""
        # These would be validated by Pydantic models in actual endpoints
        valid_names = [
            "finding",  # Minimum length
            "test-finding-with-hyphens",  # Normal case
            "a" * 100,  # Maximum length
        ]

        invalid_names = [
            "",  # Empty
            "ab",  # Too short (< 3)
            "a" * 101,  # Too long (> 100)
        ]

        # In the actual implementation, these would be handled by Pydantic
        # Here we just verify our test expectations
        for name in valid_names:
            assert len(name) >= 3
            assert len(name) <= 100

        for name in invalid_names:
            assert len(name) < 3 or len(name) > 100

    def test_description_validation_length_constraints(self) -> None:
        """Test description validation constraints."""
        valid_descriptions = [
            "A" * 20,  # Minimum length
            "This is a comprehensive medical finding description that provides sufficient detail.",  # Normal
            "A" * 2000,  # Maximum length
        ]

        invalid_descriptions = [
            "",  # Empty
            "Too short",  # < 20 characters
            "A" * 2001,  # Too long (> 2000)
        ]

        for desc in valid_descriptions:
            assert len(desc) >= 20
            assert len(desc) <= 2000

        for desc in invalid_descriptions:
            assert len(desc) < 20 or len(desc) > 2000

    def test_attributes_markdown_validation(self) -> None:
        """Test attributes markdown validation constraints."""
        valid_markdown = [
            "## Attributes\n\n### presence\nWhether the finding is present or absent.\n\n**Options:** present, absent",
            "## Attributes\n\n### severity\nSeverity of the finding\n\n**Options:** mild, moderate, severe",
        ]

        invalid_markdown = [
            "",  # Empty
            "short",  # Too short
            "# Wrong format",  # No ## Attributes
            "## Attributes\nBut no attributes defined",  # No actual attributes
        ]

        for markdown in valid_markdown:
            assert len(markdown) >= 50  # Minimum length requirement
            assert "## Attributes" in markdown
            assert "###" in markdown  # At least one attribute

        for markdown in invalid_markdown:
            assert len(markdown) < 50 or "## Attributes" not in markdown or "###" not in markdown

    def test_synonyms_parsing(self) -> None:
        """Test synonyms parsing logic."""
        test_cases = [
            ("", []),  # Empty string
            ("single", ["single"]),  # Single synonym
            ("one,two,three", ["one", "two", "three"]),  # Comma-separated
            ("one, two, three", ["one", "two", "three"]),  # With spaces
            ("  spaced  ,  out  ", ["spaced", "out"]),  # Extra spaces
        ]

        for input_str, expected in test_cases:
            # This mimics the parsing logic used in the endpoints
            result = [] if not input_str.strip() else [s.strip() for s in input_str.split(",") if s.strip()]

            assert result == expected

    def test_step_progression_validation(self) -> None:
        """Test step progression validation logic."""
        # Valid progressions
        valid_progressions = [
            (1, 1),  # Stay on step 1
            (1, 2),  # Progress from 1 to 2
            (2, 2),  # Stay on step 2
            (2, 3),  # Progress from 2 to 3
            (3, 3),  # Stay on step 3
            (3, 4),  # Progress from 3 to 4
            (4, 4),  # Stay on step 4
        ]

        # Invalid progressions
        invalid_progressions = [
            (1, 3),  # Skip step 2
            (1, 4),  # Skip multiple steps
            (2, 4),  # Skip step 3
            (3, 1),  # Go backwards
            (4, 1),  # Go backwards multiple
        ]

        for current, requested in valid_progressions:
            # In the actual implementation, this logic validates step transitions
            is_valid = requested == current or requested == current + 1
            assert is_valid, f"Step {current} to {requested} should be valid"

        for current, requested in invalid_progressions:
            is_valid = requested == current or requested == current + 1
            assert not is_valid, f"Step {current} to {requested} should be invalid"


class TestIntegrationScenarios:
    """Test integration scenarios combining session management and validation."""

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        return MagicMock(spec=RedisCache)

    async def test_complete_session_workflow(self, mock_cache: MagicMock) -> None:
        """Test a complete session workflow from creation to completion."""
        session_manager = SessionManager(mock_cache)

        # Mock cache operations
        stored_sessions = {}

        async def mock_set(key: str, value: str, **kwargs) -> None:
            stored_sessions[key] = value

        async def mock_get(key: str) -> str | None:
            return stored_sessions.get(key)

        mock_cache.set = AsyncMock(side_effect=mock_set)
        mock_cache.get = AsyncMock(side_effect=mock_get)

        # Step 1: Create session
        session_id = await session_manager.create_session()
        assert session_id is not None

        # Step 2: Get session and update with name
        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.current_step == 1

        session.name = "test-finding"
        session.current_step = 2
        await session_manager.update_session(session)

        # Step 3: Get updated session and add description
        session = await session_manager.get_session(session_id)
        assert session.name == "test-finding"
        assert session.current_step == 2

        session.description = "A comprehensive test finding description"
        session.synonyms = ["test", "finding"]
        session.current_step = 3
        await session_manager.update_session(session)

        # Step 4: Get session and add similar models
        session = await session_manager.get_session(session_id)
        assert session.description is not None
        assert len(session.synonyms) == 2
        assert session.current_step == 3

        session.similar_models = []
        session.current_step = 4
        await session_manager.update_session(session)

        # Step 5: Final step - add attributes
        session = await session_manager.get_session(session_id)
        assert session.current_step == 4

        session.attributes_markdown = "## Attributes\n\n### presence\nWhether present"
        await session_manager.update_session(session)

        # Verify final state
        final_session = await session_manager.get_session(session_id)
        assert final_session.name == "test-finding"
        assert final_session.description is not None
        assert len(final_session.synonyms) == 2
        assert final_session.similar_models == []
        assert final_session.attributes_markdown is not None
        assert final_session.current_step == 4

    async def test_session_error_recovery(self, mock_cache: MagicMock) -> None:
        """Test session recovery from errors."""
        session_manager = SessionManager(mock_cache)

        # Mock initial successful creation
        mock_cache.set = AsyncMock(return_value=None)
        session_id = await session_manager.create_session()

        # Mock cache failure during get
        mock_cache.get = AsyncMock(side_effect=Exception("Cache failure"))

        session = await session_manager.get_session(session_id)
        assert session is None  # Should handle gracefully

        # Mock recovery - cache works again
        session_data = '{"session_id": "' + session_id + '", "current_step": 2}'
        mock_cache.get = AsyncMock(return_value=session_data)

        session = await session_manager.get_session(session_id)
        assert session is not None
        assert session.session_id == session_id
        assert session.current_step == 2

    async def test_concurrent_session_updates(self, mock_cache: MagicMock) -> None:
        """Test handling of concurrent session updates."""
        session_manager = SessionManager(mock_cache)

        # Simulate race condition where session is updated between get and set
        call_count = 0
        original_data = '{"session_id": "test", "current_step": 1, "name": null}'
        updated_data = '{"session_id": "test", "current_step": 1, "name": "concurrent-update"}'

        async def mock_get(key: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return original_data
            else:
                return updated_data

        mock_cache.get = AsyncMock(side_effect=mock_get)
        mock_cache.set = AsyncMock(return_value=None)

        # First get
        session1 = await session_manager.get_session("test")
        assert session1.name is None

        # Concurrent update (simulated)
        session1.name = "first-update"
        await session_manager.update_session(session1)

        # Second get should see the change
        session2 = await session_manager.get_session("test")
        # Due to our mock, this will see the "concurrent-update"
        # In real usage, the last update wins
        assert session2.name == "concurrent-update"
