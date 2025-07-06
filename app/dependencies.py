"""Dependency injection for the application."""

from typing import Annotated

from fastapi import Depends, Request
from findingmodel.index import Index

from .database import Database, UserRepo


def get_database(request: Request) -> Database:
    """Get Database instance from FastAPI app state."""
    return request.app.state.database  # type: ignore[no-any-return]


def get_user_repo(database: Annotated[Database, Depends(get_database)]) -> UserRepo:
    """Get UserRepo instance from the database."""
    if database.user_repo is None:
        raise RuntimeError("Database not initialized or UserRepo not available")
    return database.user_repo


def get_finding_index(request: Request) -> Index:
    """Get FindingModel Index instance from FastAPI app state."""
    return request.app.state.finding_index  # type: ignore[no-any-return]
