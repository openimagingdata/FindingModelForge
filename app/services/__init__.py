"""Service layer with business logic extracted from routers.

Services are pure Python classes with no FastAPI dependencies.
They handle business logic and delegate to repositories for data access.
"""

from .comment_service import CommentService  # noqa: F401


class ServiceError(Exception):
    """Base exception for service layer errors."""

    pass


class NotFoundError(ServiceError):
    """Raised when a requested resource is not found."""

    pass


class AuthorizationError(ServiceError):
    """Raised when user lacks permission for an operation."""

    pass
