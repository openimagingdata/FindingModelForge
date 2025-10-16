"""Draft management router module."""

from fastapi import APIRouter

# Import modular routers (all endpoints now extracted)
from app.routers.drafts.comments import router as comments_router
from app.routers.drafts.mutations import router as mutations_router
from app.routers.drafts.views import router as views_router
from app.routers.drafts.workflows import router as workflows_router

# Create a combined router that includes all focused routers
router = APIRouter()

# Include all modular routers with appropriate tags
router.include_router(views_router, tags=["drafts-views"])
router.include_router(mutations_router, tags=["drafts-mutations"])
router.include_router(comments_router, tags=["drafts-comments"])
router.include_router(workflows_router, tags=["drafts-workflows"])

__all__ = ["router"]
