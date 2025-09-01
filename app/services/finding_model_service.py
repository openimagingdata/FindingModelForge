"""Finding Model service with browsing, caching, and slug operations."""

import re
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import httpx
from fastapi import HTTPException
from findingmodel import FindingModelFull

from app.cache import RedisCache
from app.config import logger, settings
from app.database import CommentRepo, UserRepo
from app.models import Comment, CommentThread, User
from app.utils.slug import generate_slug_variants, normalize_for_cache, slugify

from . import NotFoundError
from .comment_helpers import (
    add_to_comment_index,
    check_rate_limit,
    get_blacklist_user_ids,
    validate_comment_content,
    validate_parent_comment,
)


class FindingModelService:
    """Service for finding model operations including browsing and caching."""

    def __init__(self, index: Any, cache: RedisCache, comment_repo: CommentRepo, user_repo: UserRepo) -> None:
        """Initialize with required dependencies.

        Args:
            index: FindingModel index for database queries
            cache: Redis cache for performance optimization
            comment_repo: Repository for comment operations
            user_repo: Repository for user operations
        """
        self.index = index
        self.cache = cache
        self.comment_repo = comment_repo
        self.user_repo = user_repo

    async def list_models(
        self, search: str | None = None, page: int = 1, per_page: int = 20
    ) -> tuple[list[dict[str, Any]], int]:
        """Get paginated list of finding models with optional search.

        Args:
            search: Optional search query
            page: Page number (1-based)
            per_page: Items per page

        Returns:
            Tuple of (models_list, total_count)
        """
        # Get all models first
        all_models = await self._get_finding_models_list()

        # Apply search filter if provided
        if search and search.strip():
            search_lower = search.strip().lower()
            filtered_models = [model for model in all_models if search_lower in model["name"].lower()]
        else:
            filtered_models = all_models

        # Calculate pagination
        total_count = len(filtered_models)
        start_idx = (page - 1) * per_page
        end_idx = start_idx + per_page

        # Return paginated results
        paginated_models = filtered_models[start_idx:end_idx]

        return paginated_models, total_count

    async def get_model_by_slug(self, slug: str) -> tuple[FindingModelFull, Any]:
        """Get finding model by slug with caching.

        Args:
            slug: URL slug for the finding model

        Returns:
            Tuple of (finding_model, index_entry)

        Raises:
            NotFoundError: If model not found
        """
        try:
            return await self._get_finding_model_with_cache(slug)
        except Exception as e:
            if "not found" in str(e).lower():
                raise NotFoundError(f"Finding model '{slug}' not found") from e
            raise

    async def search_in_index(self, slug: str) -> Any:
        """Search for a model in the index by slug.

        Args:
            slug: URL slug to search for

        Returns:
            Index entry if found, None otherwise
        """
        raw_slug = (slug or "").strip().lower()
        candidates = generate_slug_variants(raw_slug)

        for candidate in candidates:
            try:
                index_entry = await self.index.get(candidate)
                if index_entry:
                    return index_entry
            except Exception:
                continue

        return None

    async def _get_finding_models_list(self) -> list[dict[str, Any]]:
        """Shared logic to fetch the finding models list with caching.

        Returns:
            List of finding model dictionaries with id, name, and slug
        """
        # Check cache first
        finding_models = await self.cache.get_finding_models()
        if finding_models:
            logger.debug("Cache hit for finding models list")
            return finding_models

        logger.debug("Cache miss for finding models list, fetching from index")

        # Fetch all finding models from the index
        # Use a case-insensitive sort by adding a computed field for lowercase name
        finding_models_data: list[dict[str, Any]] = await self.index.index_collection.aggregate(
            [
                {"$addFields": {"name_lower": {"$toLower": "$name"}}},
                {"$sort": {"name_lower": 1}},
                {"$project": {"name_lower": 0}},  # Exclude the helper field from results
            ]
        ).to_list(length=None)

        if not finding_models_data:
            logger.warning("No finding models found in index")
            return []

        finding_models = [
            {"id": model["oifm_id"], "name": model["name"], "slug": slugify(model["name"])}
            for model in finding_models_data
        ]

        # Cache the finding models list for 1 hour
        await self.cache.set_finding_models(finding_models)

        return finding_models

    async def _get_finding_model_with_cache(
        self,
        slug: str,
    ) -> tuple[FindingModelFull, Any]:
        """Shared logic to fetch a finding model with caching.

        Args:
            slug: URL slug for the finding model

        Returns:
            Tuple of (finding_model, index_entry)

        Raises:
            NotFoundError: If model not found in index or GitHub
        """
        # Prepare candidate lookups: prefer the space-normalized variant first (backward-compatible
        # with existing tests and behavior), then try the raw slug and separator swaps so we handle
        # names that truly include hyphens like "acro-osteolysis".
        raw_slug = (slug or "").strip().lower()
        candidates = generate_slug_variants(raw_slug)

        index_entry = None
        matched_variant = None
        for candidate in candidates:
            try:
                index_entry = await self.index.get(candidate)
            except Exception:
                index_entry = None
            if index_entry:
                matched_variant = candidate
                break

        if not index_entry:
            # Fallback: query the backing collection by a flexible regex that allows
            # spaces, hyphens, or underscores between tokens, to handle cases like
            # "bow-tie" vs "bow tie".
            tokens = [t for t in re.split(r"[-_\s]+", raw_slug) if t]
            if tokens:
                sep = r"[\s\-_]+"
                pattern = "^" + sep.join(re.escape(t) for t in tokens) + "$"
                try:
                    doc = await self.index.index_collection.find_one({"name": {"$regex": pattern, "$options": "i"}})
                except Exception:
                    doc = None
                if not doc:
                    # Try matching by filename if name lookup fails
                    base = normalize_for_cache(raw_slug).replace(" ", "_")
                    filename_regex = rf"{re.escape(base)}.*\.fm\.json$"
                    try:
                        doc = await self.index.index_collection.find_one(
                            {"filename": {"$regex": filename_regex, "$options": "i"}}
                        )
                    except Exception:
                        doc = None
                if doc and doc.get("filename"):
                    index_entry = SimpleNamespace(
                        filename=doc.get("filename"),
                        name=doc.get("name"),
                        description=doc.get("description"),
                    )
                    matched_variant = raw_slug
            if not index_entry:
                raise NotFoundError(f"Finding model '{raw_slug}' not found in index")

        # Use the space-normalized variant as the canonical cache key to remain compatible
        # with existing expectations/tests while ensuring consistent keys.
        cache_slug = normalize_for_cache(raw_slug)

        # Check cache first
        finding_model = await self.cache.get_finding_model(cache_slug)
        if finding_model:
            logger.debug(
                f"Cache hit for finding model '{raw_slug}' "
                f"(matched variant: {matched_variant}, cache key: {cache_slug})"
            )
        else:
            logger.debug(
                f"Cache miss for finding model '{raw_slug}' (matched variant: {matched_variant}), fetching from GitHub"
            )

            # Extract filename from index entry
            if not index_entry.filename:
                raise NotFoundError("Finding model entry missing filename")

            # Construct the GitHub raw URL
            github_url = f"{settings.finding_models_github_base_url}{index_entry.filename}"
            logger.debug(f"Fetching finding model from: {github_url}")

            # Fetch the finding model JSON from GitHub
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(github_url)
                    response.raise_for_status()
                    finding_model = FindingModelFull.model_validate_json(response.text)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 404:
                        raise NotFoundError(f"Finding model file not found on GitHub: {github_url}") from e
                    raise
                except Exception as e:
                    raise NotFoundError(f"Failed to fetch finding model from GitHub: {str(e)}") from e

            # Cache the result
            await self.cache.set_finding_model(cache_slug, finding_model)
            logger.debug(f"Cached finding model '{raw_slug}' (cache key: {cache_slug}) for future requests")

        return finding_model, index_entry

    async def get_by_oifm_id(self, oifm_id: str) -> Any:
        """Get finding model by OIFM ID.

        Args:
            oifm_id: The finding model ID

        Returns:
            Index entry if found, None otherwise
        """
        try:
            return await self.index.index_collection.find_one({"oifm_id": oifm_id})
        except Exception:
            return None

    async def get_comments_for_model(self, oifm_id: str) -> CommentThread | None:
        """Get comment thread for a finding model.

        Args:
            oifm_id: The finding model ID

        Returns:
            CommentThread if exists, None otherwise
        """
        return await self.comment_repo.get_thread("finding_model", oifm_id)

    async def add_comment_to_model(
        self, oifm_id: str, user: User, content: str, parent_id: str | None = None
    ) -> Comment:
        """Add comment to finding model with validations.

        Args:
            oifm_id: The finding model ID
            user: Current user object
            content: Comment content (1-2000 chars)
            parent_id: Optional parent comment ID for replies

        Returns:
            The created Comment

        Raises:
            ValueError: If content invalid
            HTTPException: If rate limited, blacklisted, or parent invalid
        """
        # 1. Check if user is blacklisted
        blacklist = get_blacklist_user_ids()
        if user.id in blacklist:
            raise HTTPException(403, "User is not allowed to comment")

        # 2. Validate content
        content = validate_comment_content(content)

        # 3. Check rate limit
        user_doc = await self.user_repo.collection.find_one({"id": user.id})
        if not user_doc or not check_rate_limit(user_doc):
            raise HTTPException(429, "Rate limit exceeded. Please wait before commenting again.")

        # 4. If parent_id provided, validate it's a top-level comment
        if parent_id:
            thread = await self.comment_repo.get_thread("finding_model", oifm_id)
            if thread:
                validate_parent_comment(thread, parent_id)

        # 5. Create comment
        comment = Comment(
            user_id=user.id,
            user_name=user.login,
            user_avatar_url=user.avatar_url,
            content=content,
            created_at=datetime.now(UTC),
        )

        # 6. Add to thread
        if parent_id:
            # thread is guaranteed to exist because validate_parent_comment would have raised if not
            thread = await self.comment_repo.get_thread("finding_model", oifm_id)
            if thread:
                await self.comment_repo.add_reply(thread.id, parent_id, comment)
        else:
            await self.comment_repo.add_comment("finding_model", oifm_id, comment)

        # 7. Track in user's comment index
        # Get finding model name for display
        model = await self.get_by_oifm_id(oifm_id)
        finding_name = model.get("name") if model else oifm_id
        await add_to_comment_index(self.user_repo, user.id, finding_name, "finding_model", oifm_id, comment.id)

        return comment

    async def report_model_comment(self, oifm_id: str, comment_id: str, user_id: int) -> None:
        """Report a comment on a finding model.

        Args:
            oifm_id: The finding model ID
            comment_id: The comment to report
            user_id: The user reporting

        Raises:
            HTTPException: If comment not found or already reported by user
        """
        thread = await self.comment_repo.get_thread("finding_model", oifm_id)
        if not thread:
            raise HTTPException(404, "Comment thread not found")

        # Check if already reported by this user
        for comment in thread.comments:
            if comment.id == comment_id and comment.reported_by == user_id:
                raise HTTPException(400, "You have already reported this comment")
            for reply in comment.replies:
                if reply.id == comment_id and reply.reported_by == user_id:
                    raise HTTPException(400, "You have already reported this comment")

        success = await self.comment_repo.report_comment(thread.id, comment_id, user_id)
        if not success:
            raise HTTPException(404, "Comment not found")
