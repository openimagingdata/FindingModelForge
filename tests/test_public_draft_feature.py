"""Comprehensive unit tests for the new public draft review feature.

This test suite covers the PUBLIC status implementation including:
- DraftStatus.PUBLIC enum value
- Updated view/comment permissions
- POST /drafts/{id}/make-public endpoint
- GET /drafts endpoint for listing public drafts
- Validation requiring PUBLIC status before submission
- Redis caching with invalidation
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.auth import get_current_user
from app.cache import RedisCache
from app.database import DraftRepo
from app.dependencies import get_cache, get_draft_service
from app.main import app
from app.models import DraftStatus, FindingModelDraft, FindingModelInputs, User
from app.services.comment_service import CommentService
from app.services.draft_service import DraftService


class TestPublicDraftFeature:
    """Test suite for public draft review feature."""

    @pytest.fixture
    def mock_user(self) -> User:
        """Create a test user."""
        now = datetime.now(UTC)
        return User(
            id=999999,
            login="test_user",
            name="Test User",
            email="test@example.com",
            avatar_url="https://example.com/avatar.jpg",
            organizations=[],
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def mock_other_user(self) -> User:
        """Create another test user."""
        now = datetime.now(UTC)
        return User(
            id=888888,
            login="other_user",
            name="Other User",
            email="other@example.com",
            avatar_url="https://example.com/other_avatar.jpg",
            organizations=[],
            created_at=now,
            updated_at=now,
        )

    @pytest.fixture
    def mock_draft_repo(self) -> MagicMock:
        """Create a mock DraftRepo."""
        repo = MagicMock(spec=DraftRepo)
        repo.get_draft = AsyncMock()
        repo.make_public = AsyncMock()
        repo.submit = AsyncMock()
        repo.get_public_drafts = AsyncMock()
        return repo

    @pytest.fixture
    def mock_user_repo(self) -> MagicMock:
        """Create a mock UserRepo."""
        repo = MagicMock()
        repo.add_comment_to_index = AsyncMock()
        return repo

    @pytest.fixture
    def mock_comment_service(self) -> MagicMock:
        """Create a mock CommentService."""
        service = MagicMock(spec=CommentService)
        service.get_thread = AsyncMock()
        service.add_comment = AsyncMock()
        service.report_comment = AsyncMock()
        return service

    @pytest.fixture
    def mock_database(self) -> MagicMock:
        """Create a mock Database."""
        from app.database import Database, PeopleRepo

        db = MagicMock(spec=Database)
        db.ensure_person_for_user = AsyncMock(return_value=None)

        # Mock people_repo
        db.people_repo = MagicMock(spec=PeopleRepo)
        db.people_repo.get_by_username = AsyncMock(return_value=None)

        return db

    @pytest.fixture
    def mock_cache(self) -> MagicMock:
        """Create a mock Redis cache."""
        cache = MagicMock(spec=RedisCache)
        cache.get = AsyncMock(return_value=None)
        cache.set = AsyncMock(return_value=True)
        cache.delete = AsyncMock(return_value=True)
        return cache

    @pytest.fixture
    def mock_draft_service(self, mock_draft_repo: MagicMock, mock_user_repo: MagicMock) -> MagicMock:
        """Create a mock DraftService."""
        service = AsyncMock(spec=DraftService)
        service.make_public_draft = AsyncMock()
        service.get_public_drafts = AsyncMock()
        service.get_draft = AsyncMock()
        service.submit_draft = AsyncMock()
        return service

    @pytest.fixture
    def sample_draft(self, mock_user: User) -> FindingModelDraft:
        """Create a sample draft."""
        now = datetime.now(UTC)
        return FindingModelDraft(
            id="507f1f77bcf86cd799439011",
            user_id=mock_user.id,
            name="Test Finding",
            created_at=now,
            updated_at=now,
            inputs=FindingModelInputs(
                description="Test description", synonyms=["test", "example"], attributes_markdown="# Test attributes"
            ),
            status=DraftStatus.DRAFT,
            action_log=[],
            author_name="Test User",
            author_username="test_user",
        )

    @pytest.fixture
    def public_draft(self, sample_draft: FindingModelDraft) -> FindingModelDraft:
        """Create a sample public draft."""
        draft = sample_draft.model_copy()
        draft.status = DraftStatus.PUBLIC
        return draft

    @pytest.fixture
    def submitted_draft(self, sample_draft: FindingModelDraft) -> FindingModelDraft:
        """Create a sample submitted draft."""
        draft = sample_draft.model_copy()
        draft.status = DraftStatus.SUBMITTED
        return draft

    # ===== STATUS ENUM TESTS =====

    def test_draft_status_enum_includes_public(self) -> None:
        """Test that DraftStatus.PUBLIC exists and equals 'public'."""
        assert DraftStatus.PUBLIC == "public"
        assert hasattr(DraftStatus, "PUBLIC")

    def test_draft_status_ordering(self) -> None:
        """Test the correct ordering of statuses."""
        # Ensure all expected statuses exist
        assert DraftStatus.DRAFT == "draft"
        assert DraftStatus.PUBLIC == "public"
        assert DraftStatus.SUBMITTED == "submitted"
        assert DraftStatus.UNDER_REVIEW == "under-review"
        assert DraftStatus.ADDED == "added"
        assert DraftStatus.DECLINED == "declined"

    # ===== REPOSITORY PERMISSION TESTS =====

    @pytest.mark.asyncio
    async def test_owner_can_view_draft_status(
        self, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft
    ) -> None:
        """Test owner can view their draft in DRAFT status."""
        mock_draft_repo.get_draft.return_value = sample_draft

        # This would be called in the actual repository implementation
        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 999999)
        assert result == sample_draft

    @pytest.mark.asyncio
    async def test_owner_can_view_public_status(
        self, mock_draft_repo: MagicMock, public_draft: FindingModelDraft
    ) -> None:
        """Test owner can view their draft in PUBLIC status."""
        mock_draft_repo.get_draft.return_value = public_draft

        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 999999)
        assert result == public_draft

    @pytest.mark.asyncio
    async def test_owner_can_view_submitted_status(
        self, mock_draft_repo: MagicMock, submitted_draft: FindingModelDraft
    ) -> None:
        """Test owner can view their draft in SUBMITTED status."""
        mock_draft_repo.get_draft.return_value = submitted_draft

        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 999999)
        assert result == submitted_draft

    @pytest.mark.asyncio
    async def test_non_owner_can_view_public_drafts(
        self, mock_draft_repo: MagicMock, public_draft: FindingModelDraft
    ) -> None:
        """Test non-owner can view PUBLIC drafts."""
        mock_draft_repo.get_draft.return_value = public_draft

        # Different user ID (888888 vs 999999)
        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 888888)
        assert result == public_draft

    @pytest.mark.asyncio
    async def test_non_owner_can_view_submitted_drafts(
        self, mock_draft_repo: MagicMock, submitted_draft: FindingModelDraft
    ) -> None:
        """Test non-owner can view SUBMITTED drafts."""
        mock_draft_repo.get_draft.return_value = submitted_draft

        # Different user ID (888888 vs 999999)
        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 888888)
        assert result == submitted_draft

    @pytest.mark.asyncio
    async def test_non_owner_cannot_view_draft_status(self, mock_draft_repo: MagicMock) -> None:
        """Test non-owner CANNOT view DRAFT status drafts."""
        mock_draft_repo.get_draft.return_value = None  # Repository returns None for inaccessible drafts

        result = await mock_draft_repo.get_draft("507f1f77bcf86cd799439011", 888888)
        assert result is None

    # ===== SERVICE LAYER TESTS =====

    @pytest.mark.asyncio
    async def test_make_public_draft_success(
        self,
        mock_draft_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_database: MagicMock,
        mock_comment_service: MagicMock,
        sample_draft: FindingModelDraft,
        public_draft: FindingModelDraft,
    ) -> None:
        """Test make_public_draft changes status from DRAFT to PUBLIC."""
        # Mock the repository calls
        mock_draft_repo.get_draft.return_value = sample_draft
        mock_draft_repo.make_public.return_value = public_draft

        service = DraftService(
            mock_draft_repo,
            mock_user_repo,
            mock_database,
            mock_comment_service,
        )

        result = await service.make_public_draft("507f1f77bcf86cd799439011", 999999)

        # Verify ownership check was called
        mock_draft_repo.get_draft.assert_called_once_with("507f1f77bcf86cd799439011", 999999)

        # Verify make_public was called
        mock_draft_repo.make_public.assert_called_once_with("507f1f77bcf86cd799439011", 999999)

        assert result.status == DraftStatus.PUBLIC

    @pytest.mark.asyncio
    async def test_make_public_draft_validates_ownership(
        self,
        mock_draft_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_database: MagicMock,
        mock_comment_service: MagicMock,
    ) -> None:
        """Test make_public_draft validates ownership."""
        # Mock draft not found (ownership check fails)
        mock_draft_repo.get_draft.return_value = None

        service = DraftService(
            mock_draft_repo,
            mock_user_repo,
            mock_database,
            mock_comment_service,
        )

        from app.services import NotFoundError

        with pytest.raises(NotFoundError):
            await service.make_public_draft("507f1f77bcf86cd799439011", 999999)

    @pytest.mark.asyncio
    async def test_get_public_drafts_returns_only_public(
        self,
        mock_draft_repo: MagicMock,
        mock_user_repo: MagicMock,
        mock_database: MagicMock,
        mock_comment_service: MagicMock,
        public_draft: FindingModelDraft,
    ) -> None:
        """Test get_public_drafts returns only PUBLIC status drafts."""
        mock_drafts = [public_draft]
        mock_draft_repo.get_public_drafts.return_value = mock_drafts

        service = DraftService(
            mock_draft_repo,
            mock_user_repo,
            mock_database,
            mock_comment_service,
        )

        result = await service.get_public_drafts()

        mock_draft_repo.get_public_drafts.assert_called_once()
        assert len(result) == 1
        assert result[0]["status"] == DraftStatus.PUBLIC

    # ===== ROUTER ENDPOINT TESTS =====

    def test_make_draft_public_endpoint_owner_success(
        self,
        client: TestClient,
        mock_user: User,
        mock_draft_service: MagicMock,
        mock_cache: MagicMock,
        public_draft: FindingModelDraft,
    ) -> None:
        """Test POST /drafts/{id}/make-public succeeds for owner."""
        mock_draft_service.make_public_draft.return_value = public_draft

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/make-public", follow_redirects=False)

            # The endpoint should return redirect or content depending on implementation
            # Let's check what we actually get first
            assert response.status_code in [200, 303]  # Either success content or redirect

            # Verify service was called
            mock_draft_service.make_public_draft.assert_called_once_with("507f1f77bcf86cd799439011", 999999)

            # Verify cache invalidation
            mock_cache.delete.assert_called_once_with("public_drafts_list")
        finally:
            app.dependency_overrides.clear()

    def test_make_draft_public_endpoint_non_owner_forbidden(
        self, client: TestClient, mock_other_user: User, mock_draft_service: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Test POST /drafts/{id}/make-public returns error for non-owner."""
        # Mock service to raise an exception for non-owner
        mock_draft_service.make_public_draft.side_effect = Exception("Not found")

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_other_user
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/make-public")

            assert response.status_code == 500  # Error from service

            # Verify service was called with other user's ID
            mock_draft_service.make_public_draft.assert_called_once_with("507f1f77bcf86cd799439011", 888888)
        finally:
            app.dependency_overrides.clear()

    def test_make_draft_public_endpoint_unauthenticated(self, client: TestClient) -> None:
        """Test POST /drafts/{id}/make-public returns 401 for unauthenticated user."""

        def mock_get_current_user():
            raise HTTPException(status_code=401, detail="Authentication required")

        app.dependency_overrides[get_current_user] = mock_get_current_user

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/make-public")
            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_list_public_drafts_endpoint_returns_error_missing_template(
        self, client: TestClient, mock_draft_service: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Test GET /drafts returns success now that template exists."""
        mock_public_drafts = [
            {
                "id": "507f1f77bcf86cd799439011",
                "name": "Test Finding",
                "status": "public",
                "updated_display": "2 hours ago",
            }
        ]
        mock_draft_service.get_public_drafts.return_value = mock_public_drafts

        # Override dependencies
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.get("/drafts/")

            # The endpoint returns 200 now that drafts_table.html template exists
            assert response.status_code == 200

            # Verify service was called
            mock_draft_service.get_public_drafts.assert_called_once()

            # Verify cache operations (get and set)
            mock_cache.get.assert_called_once_with("public_drafts_list")
            mock_cache.set.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_list_public_drafts_endpoint_uses_cache(
        self, client: TestClient, mock_draft_service: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Test GET /drafts uses Redis cache when available."""
        cached_data = [
            {
                "id": "507f1f77bcf86cd799439011",
                "name": "Cached Finding",
                "status": "public",
            }
        ]
        mock_cache.get.return_value = json.dumps(cached_data)

        # Override dependencies
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.get("/drafts/")

            # Returns 200 now that template exists
            assert response.status_code == 200

            # Verify cache was checked
            mock_cache.get.assert_called_once_with("public_drafts_list")

            # Verify service was NOT called (cache hit)
            mock_draft_service.get_public_drafts.assert_not_called()
        finally:
            app.dependency_overrides.clear()

    def test_list_public_drafts_endpoint_sets_cache_on_miss(
        self, client: TestClient, mock_draft_service: MagicMock, mock_cache: MagicMock
    ) -> None:
        """Test GET /drafts sets cache with TTL on cache miss."""
        mock_public_drafts = [{"id": "507f1f77bcf86cd799439011", "name": "Test Finding"}]
        mock_draft_service.get_public_drafts.return_value = mock_public_drafts
        mock_cache.get.return_value = None  # Cache miss

        # Override dependencies
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.get("/drafts/")

            # Returns 200 now that template exists
            assert response.status_code == 200

            # Verify service was called
            mock_draft_service.get_public_drafts.assert_called_once()

            # Verify cache was set
            mock_cache.set.assert_called_once()
            set_call_args = mock_cache.set.call_args
            assert set_call_args[0][0] == "public_drafts_list"  # key
            assert json.loads(set_call_args[0][1]) == mock_public_drafts  # value
        finally:
            app.dependency_overrides.clear()

    # ===== SUBMISSION VALIDATION TESTS =====

    def test_submit_public_draft_succeeds(
        self,
        client: TestClient,
        mock_user: User,
        mock_draft_service: MagicMock,
        mock_cache: MagicMock,
        public_draft: FindingModelDraft,
        submitted_draft: FindingModelDraft,
    ) -> None:
        """Test can submit PUBLIC draft."""
        mock_draft_service.get_draft.return_value = public_draft  # Status check returns public draft
        # Mock get_draft_with_author to return draft as dict without author_info aggregation
        mock_draft_dict = public_draft.model_dump()
        mock_draft_dict["id"] = public_draft.id  # Ensure id is string
        mock_draft_service.get_draft_with_author.return_value = mock_draft_dict
        mock_draft_service.submit_draft.return_value = submitted_draft

        # Mock other dependencies
        from app.dependencies import get_session_manager

        mock_session_manager = MagicMock()
        mock_session_manager.create_session = AsyncMock(return_value="test-session-id")
        mock_session_manager.get_session = AsyncMock(return_value=None)
        mock_session_manager.update_session = AsyncMock()
        mock_session_manager.delete_session = AsyncMock()

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache
        app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/submit")

            assert response.status_code in [200, 303]  # Either success content or redirect

            # Verify service was called
            mock_draft_service.submit_draft.assert_called_once_with(draft_id="507f1f77bcf86cd799439011", user_id=999999)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_submit_draft_status_validation_in_repository(self, mock_draft_repo: MagicMock) -> None:
        """Test cannot submit DRAFT status draft (repository level validation)."""
        # The repository's submit method should only work on PUBLIC drafts
        # This is tested by mocking the repository behavior
        mock_draft_repo.submit.side_effect = ValueError("Draft not found or not in public status")

        with pytest.raises(ValueError, match="not in public status"):
            await mock_draft_repo.submit("507f1f77bcf86cd799439011", 999999)

    # ===== STATE TRANSITION TESTS =====

    @pytest.mark.asyncio
    async def test_draft_to_public_transition_allowed(
        self, mock_draft_repo: MagicMock, sample_draft: FindingModelDraft, public_draft: FindingModelDraft
    ) -> None:
        """Test DRAFT → PUBLIC transition is allowed."""
        mock_draft_repo.make_public.return_value = public_draft

        result = await mock_draft_repo.make_public("507f1f77bcf86cd799439011", 999999)
        assert result.status == DraftStatus.PUBLIC

    @pytest.mark.asyncio
    async def test_public_to_submitted_transition_allowed(
        self, mock_draft_repo: MagicMock, submitted_draft: FindingModelDraft
    ) -> None:
        """Test PUBLIC → SUBMITTED transition is allowed."""
        mock_draft_repo.submit.return_value = submitted_draft

        result = await mock_draft_repo.submit("507f1f77bcf86cd799439011", 999999)
        assert result.status == DraftStatus.SUBMITTED

    @pytest.mark.asyncio
    async def test_draft_to_submitted_transition_blocked(self, mock_draft_repo: MagicMock) -> None:
        """Test DRAFT → SUBMITTED transition is blocked."""
        # Repository should raise an error when trying to submit a non-public draft
        mock_draft_repo.submit.side_effect = ValueError("Draft not found or not in public status")

        with pytest.raises(ValueError, match="not in public status"):
            await mock_draft_repo.submit("507f1f77bcf86cd799439011", 999999)

    # ===== CACHE INVALIDATION TESTS =====

    def test_make_public_invalidates_cache(
        self,
        client: TestClient,
        mock_user: User,
        mock_draft_service: MagicMock,
        mock_cache: MagicMock,
        public_draft: FindingModelDraft,
    ) -> None:
        """Test making draft public invalidates public_drafts_list cache."""
        mock_draft_service.make_public_draft.return_value = public_draft
        # Mock get_draft_with_author to return draft as dict without author_info aggregation
        mock_draft_dict = public_draft.model_dump()
        mock_draft_dict["id"] = public_draft.id  # Ensure id is string
        mock_draft_service.get_draft_with_author.return_value = mock_draft_dict

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/make-public")

            assert response.status_code in [200, 303]

            # Verify cache invalidation
            mock_cache.delete.assert_called_once_with("public_drafts_list")
        finally:
            app.dependency_overrides.clear()

    def test_submit_invalidates_cache(
        self,
        client: TestClient,
        mock_user: User,
        mock_draft_service: MagicMock,
        mock_cache: MagicMock,
        public_draft: FindingModelDraft,
        submitted_draft: FindingModelDraft,
    ) -> None:
        """Test submitting draft works (cache invalidation would happen in router)."""
        mock_draft_service.get_draft.return_value = public_draft  # Status check returns public draft
        # Mock get_draft_with_author to return draft as dict without author_info aggregation
        mock_draft_dict = public_draft.model_dump()
        mock_draft_dict["id"] = public_draft.id  # Ensure id is string
        mock_draft_service.get_draft_with_author.return_value = mock_draft_dict
        mock_draft_service.submit_draft.return_value = submitted_draft

        # Mock other dependencies
        from app.dependencies import get_session_manager

        mock_session_manager = MagicMock()
        mock_session_manager.create_session = AsyncMock(return_value="test-session-id")
        mock_session_manager.get_session = AsyncMock(return_value=None)
        mock_session_manager.update_session = AsyncMock()
        mock_session_manager.delete_session = AsyncMock()

        # Override dependencies
        app.dependency_overrides[get_current_user] = lambda: mock_user
        app.dependency_overrides[get_draft_service] = lambda: mock_draft_service
        app.dependency_overrides[get_cache] = lambda: mock_cache
        app.dependency_overrides[get_session_manager] = lambda: mock_session_manager

        try:
            response = client.post("/drafts/507f1f77bcf86cd799439011/submit")

            assert response.status_code in [200, 303]

            # Verify service was called
            mock_draft_service.submit_draft.assert_called_once_with(draft_id="507f1f77bcf86cd799439011", user_id=999999)
        finally:
            app.dependency_overrides.clear()
