# MyPy Pre-commit Hook Fixes

## Summary

Fixed all mypy errors that occurred in the pre-commit hook environment but not in local development.

## Issues Fixed

### 1. Import-not-found Errors

**Problem**: Pre-commit hook couldn't find `motor.motor_asyncio`, `pymongo`, and `pymongo.errors` modules.

**Root Cause**: The pre-commit mypy hook runs in its own isolated environment without access to the project's dependencies.

**Solution**:

- Added required dependencies to the mypy hook's `additional_dependencies` in `.pre-commit-config.yaml`
- Added mypy overrides for motor/pymongo modules to ignore missing imports in `pyproject.toml`

### 2. Any Return Type Error

**Problem**: Line 124 in `app/database.py` was returning `Any` from a function declared to return `bool`.

**Root Cause**: `result.modified_count > 0` was inferring as `Any` type instead of `bool`.

**Solution**: Wrapped the expression with `bool()` to ensure explicit boolean return type.

### 3. Unused Type Ignore Comments

**Problem**: Several `# type: ignore` comments in `tests/test_user_repo.py` were flagged as unused.

**Root Cause**: The specific error codes in the ignore comments didn't match the actual mypy errors in the pre-commit environment.

**Solution**: Verified that the `# type: ignore[method-assign]` comments are actually needed for mock method assignments and kept them.

## Changes Made

### .pre-commit-config.yaml

```yaml
- id: mypy
  additional_dependencies: [pydantic, fastapi, pydantic-settings, httpx, pyjwt, pytest, loguru, uvicorn, motor, pymongo]
  args: [--config-file=pyproject.toml]
  exclude: ^zOld/
```

### pyproject.toml

```toml
[[tool.mypy.overrides]]
module = ["motor.*", "pymongo.*"]
ignore_missing_imports = true
```

### app/database.py

```python
# Line 124: Fixed Any return type issue
return bool(result.modified_count > 0)
```

## Verification

- ✅ `uv run mypy app tests` - passes locally
- ✅ `pre-commit run mypy --all-files` - passes in pre-commit environment
- ✅ `pre-commit run --all-files` - all hooks pass

## Why This Happened

The pre-commit mypy hook runs in an isolated Python environment that doesn't have access to the project's virtual environment or installed dependencies. This is by design for reproducibility and security, but it means we need to explicitly declare all dependencies the type checker needs.

The environment differences explain why:

1. Local mypy worked (had access to installed packages)
2. Pre-commit mypy failed (isolated environment without dependencies)
3. Type ignore comments appeared unused (different mypy configuration/environment)

## Best Practices

1. Always test pre-commit hooks before committing
2. Include all type-checking dependencies in the mypy hook configuration
3. Use mypy overrides for third-party libraries without good type stubs
4. Keep type ignore comments minimal and specific to the actual error codes
