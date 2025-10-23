"""Repository layer for FindingModelForge.

Repositories provide a clean abstraction over data sources:
- Read from Index (canonical, backend-agnostic)
- Write to MongoDB (drafts only)

Never write to Index - it's read-only canonical data.
"""

from .organization_repo import OrganizationRepo
from .people_repo import PeopleRepo

__all__ = ["PeopleRepo", "OrganizationRepo"]
