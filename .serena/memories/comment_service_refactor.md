# CommentService Refactor - Centralized Comment Logic

## Implementation Date
September 30, 2025

## Purpose
Centralize all comment business logic into a shared `CommentService` to eliminate code duplication and establish proper service layer separation.

## Architecture

### Service Layer Pattern
```
Router (HTTP) → Service (Business Logic) → Repository (Data Access)
```

**CommentService** acts as the single source of truth for:
- Rate limiting (3 comments per 60 seconds)
- Content validation (1-2000 characters)
- Blacklist checking
- User comment index updates
- Draft status validation
- Thread and reply management

## Implementation

### CommentService (`app/services/comment_service.py`)

Key methods:
- `get_thread(reference_type, reference_id)` - Fetch comment thread
- `add_comment(reference_type, reference_id, user, content, parent_id=None, reference_name=None)` - Add comment with full validation
- `report_comment(reference_type, reference_id, comment_id, reporting_user_id)` - Report with duplicate prevention

Supports both `"draft"` and `"finding_model"` reference types.

### Service Integration

**DraftService** delegates to CommentService:
```python
async def add_comment_to_draft(self, draft_id, user, content, parent_id=None):
    return await self.comment_service.add_comment("draft", draft_id, user, content, parent_id=parent_id)
```

**FindingModelService** delegates to CommentService:
```python
async def add_comment_to_model(self, oifm_id, user, content, parent_id=None):
    model = await self.get_by_oifm_id(oifm_id)
    return await self.comment_service.add_comment("finding_model", oifm_id, user, content, parent_id=parent_id, reference_name=model.get("name"))
```

### Router Cleanup

Routers are now thin HTTP handlers:
- No rate limiting logic (delegated to service)
- No manual user index updates (handled by service)
- Simple delegation to service methods

## Benefits

1. **Single Source of Truth** - Rate limiting logic exists only in CommentService
2. **No Code Duplication** - Shared logic between drafts and finding models
3. **Proper Separation** - Business logic in services, not routers
4. **Easier Testing** - Unit test service, integration test routers
5. **Maintainability** - Changes to comment logic only need updates in one place

## Testing

- **Unit tests**: `tests/test_services/test_comment_service.py` (comprehensive)
- **Integration tests**: Updated to mock service-level rate limiting
- **Coverage**: 491 tests passing, 79.50% coverage maintained

## Usage Pattern for New Features

When adding comments to new entity types:

1. Add CommentService to your service class constructor
2. Delegate comment operations to `comment_service.add_comment()`
3. Pass appropriate `reference_type` and `reference_id`
4. Router only handles HTTP concerns (parsing, responses)

Example:
```python
class MyNewService:
    def __init__(self, comment_service: CommentService):
        self.comment_service = comment_service

    async def add_comment(self, entity_id, user, content):
        return await self.comment_service.add_comment(
            "my_entity_type",
            entity_id,
            user,
            content,
            reference_name=self.entity_name
        )
```

## Documentation

- **CHANGELOG.md** - Added to Changed section (September 30, 2025)
- **docs/RECENT_UPDATES_SUMMARY.md** - Added refactor section
- **app/CLAUDE.md** - Added Service Layer and Comment System sections
- **tasks/shared-comment-service-plan.md** - Marked complete

## Future Considerations

If adding new comment features (edit, delete, reactions):
- Add methods to CommentService
- Update both DraftService and FindingModelService simultaneously
- Maintain delegation pattern in routers
