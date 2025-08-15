# Code Style and Conventions

## Type Safety
- **Always** use type hints for function signatures
- Use `Annotated` for FastAPI dependencies
- Prefer explicit types over `Any`
- Enable MyPy strict mode compliance (configured in pyproject.toml)

## Async Patterns
- Always use async/await for I/O operations
- Dependency injection pattern with FastAPI's system
- Cache-first patterns with Redis integration

```python
# Standard async pattern
async def get_finding_model(
    model_id: str,
    database: DatabaseDep,
    cache: CacheDep
) -> FindingModel | None:
    # Check cache first
    if cached := await cache.get(f"model:{model_id}"):
        return FindingModel.model_validate_json(cached)
    
    # Fetch from database
    if doc := await database.finding_models.find_one({"_id": model_id}):
        await cache.set(f"model:{model_id}", doc.model_dump_json())
        return FindingModel.model_validate(doc)
    
    return None
```

## Frontend Patterns
- **CRITICAL**: Use Flowbite's data-attribute patterns, NOT custom JavaScript
- Use Jinja2 macros for reusable components
- Alpine.js for reactivity, not custom event handling

## Code Quality Tools
- **Ruff**: Formatting and linting (replaces Black, isort, flake8)
- **MyPy**: Static type checking with strict mode
- **pytest**: Testing with asyncio mode
- **pre-commit**: Git hooks for quality enforcement

## Project Structure
- `app/` - FastAPI application
- `templates/` - Jinja2 templates with components
- `static/` - Compiled assets
- `src/` - Frontend source files
- `tests/` - pytest test suite with unit/integration separation