# Unit Tests for `generate_finding_model_json()` Helper

## Context

During the drafts router refactoring, we extracted `generate_finding_model_json()` from the main router into [`app/routers/drafts/helpers.py:274-360`](app/routers/drafts/helpers.py#L274-L360). This function is currently **only tested via integration tests** but now that it's extracted, we can add focused unit tests for its business logic.

## Function Overview

**Purpose**: Generate finding model JSON from draft inputs, either via mock generation (for test users) or real AI generation.

**Key Logic Branches**:
1. **Mock generation** (when `is_test_user=True`): Creates a mock finding model with a presence attribute
2. **Source code selection**: 3-tier fallback for organization code: author.org → user.org → "OIDM"
3. **Name normalization**: Ensures mock model name is at least 5 characters (appends " Test" if shorter)

**External Dependencies** (to be mocked):
- `asyncio.sleep()` - Simulates AI processing
- `add_ids_to_model()` - Adds OIFM IDs to model
- `add_standard_codes_to_model()` - Adds standard codes (mutates in place)
- `create_model_from_markdown()` - Real AI generation (not tested here)
- `FindingModelBase.model_validate()` - Validates model structure (let it run to test our mock structure)

## Test Suite Specification

**File**: `tests/test_routers/test_generate_finding_model_json.py`

**Total Tests**: 6

### Test 1: `test_generate_mock_model_with_normal_name`

**Purpose**: Verify mock generation creates valid structure for names ≥5 characters

**Setup**:
- Draft with `name="Nodule"` (5 chars)
- `is_test_user=True`
- Mock `asyncio.sleep` (no delay)
- Mock `add_ids_to_model` to return a model with `model_dump_json()` method
- Mock `add_standard_codes_to_model` (no-op)
- Mock database with `finding_index=True`, `people.get()` returns author with `organization_code="TEST"`

**Execute**: Call `generate_finding_model_json()` with test data

**Assertions**:
1. Result is valid JSON string
2. Parse JSON and verify:
   - `name` == "Nodule" (not modified)
   - `description` matches input
   - `synonyms` matches input list
   - Has `attributes` array with 1 item
   - Attribute has `name="presence"`, `type="choice"`
   - Attribute has 2 values: "absent" and "present"
3. `add_ids_to_model` was called once with `source="TEST"`

---

### Test 2: `test_generate_mock_model_with_short_name`

**Purpose**: Verify name padding logic for names <5 characters

**Setup**:
- Draft with `name="Mass"` (4 chars)
- `is_test_user=True`
- Same mocking as Test 1

**Execute**: Call `generate_finding_model_json()`

**Assertions**:
1. Result is valid JSON
2. Parse JSON and verify `name` == "Mass Test" (padded with " Test")
3. Rest of structure is valid (description, synonyms, attributes)

---

### Test 3: `test_source_code_from_author_organization`

**Purpose**: Verify source code selection uses author.organization_code when available

**Setup**:
- `is_test_user=True` (for speed)
- Mock database:
  - `finding_index=True`
  - `people.get(current_user.login)` returns mock author with `organization_code="ACME"`
- Mock `add_ids_to_model` to capture call arguments
- User with `organizations=["ORG1", "ORG2"]`

**Execute**: Call `generate_finding_model_json()`

**Assertions**:
1. `add_ids_to_model` was called once
2. Second argument (source) == "ACME" (from author, not user orgs)

---

### Test 4: `test_source_code_from_user_organizations`

**Purpose**: Verify source code falls back to user.organizations[0] when author not found

**Setup**:
- `is_test_user=True`
- Mock database:
  - `finding_index=True`
  - `people.get(current_user.login)` returns `None` (no author)
- User with `organizations=["ORG1", "ORG2"]`
- Mock `add_ids_to_model` to capture arguments

**Execute**: Call `generate_finding_model_json()`

**Assertions**:
1. `add_ids_to_model` was called with `source="ORG1"` (first org in list)

---

### Test 5: `test_source_code_fallback_to_oidm`

**Purpose**: Verify source code defaults to "OIDM" when no author and no user orgs

**Setup**:
- `is_test_user=True`
- Mock database:
  - `finding_index=True`
  - `people.get()` returns `None`
- User with `organizations=[]` (empty list)
- Mock `add_ids_to_model`

**Execute**: Call `generate_finding_model_json()`

**Assertions**:
1. `add_ids_to_model` was called with `source="OIDM"` (default fallback)

---

### Test 6: `test_missing_finding_index_raises_assertion_error`

**Purpose**: Verify assertion fails when database.finding_index is not initialized

**Setup**:
- `is_test_user=True`
- Mock database with `finding_index=None` (or falsy value)
- Mock `add_ids_to_model` and other dependencies

**Execute**: Call `generate_finding_model_json()` within `pytest.raises(AssertionError)`

**Assertions**:
1. AssertionError is raised
2. Error message contains "FindingIndex must be initialized"

---

## Implementation Guidelines

### Imports Required

**Follow the exact import pattern from [`tests/test_routers/test_drafts_helpers.py:1-10`](tests/test_routers/test_drafts_helpers.py#L1-L10)**:

```python
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from app.models import FindingModelDraft, FindingModelInputs, User
from app.routers.drafts.helpers import generate_finding_model_json
```

### Test Data Creation Pattern

**🚨 CRITICAL**: Follow the **inline creation pattern** from [`test_drafts_helpers.py`](tests/test_routers/test_drafts_helpers.py).

**Do NOT create helper functions or fixtures.** Create objects directly in each test for consistency.

**Standard FindingModelDraft pattern** (from [`test_drafts_helpers.py:155-164`](tests/test_routers/test_drafts_helpers.py#L155-L164)):
```python
draft = FindingModelDraft(
    id="test-id",
    user_id=123,
    name="Test Draft",  # Vary this as needed per test
    status="draft",
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
    inputs=FindingModelInputs(
        description="Test description",
        synonyms=["synonym1", "synonym2"],
        attributes_markdown="## Test\n- test: value"
    ),
    action_log=[],
)
```

**Standard User pattern** (from [`test_drafts_helpers.py:165-174`](tests/test_routers/test_drafts_helpers.py#L165-L174)):
```python
user = User(
    id=123,
    login="testuser",
    name="Test User",
    email="test@example.com",
    avatar_url="",
    organizations=[],  # Vary this for source selection tests
    created_at=datetime.now(UTC),
    updated_at=datetime.now(UTC),
)
```

### Mocking Strategy

**Follow mocking patterns from [`test_drafts_helpers.py`](tests/test_routers/test_drafts_helpers.py)**:

**For `add_ids_to_model`** - Create mock that returns object with `model_dump_json()` method:
```python
# Create a mock that returns an object with model_dump_json method
mock_model = Mock()
mock_model.model_dump_json.return_value = json.dumps({
    "name": "Test",
    "description": "Test description",
    "synonyms": ["synonym1", "synonym2"],
    "attributes": [
        {
            "name": "presence",
            "type": "choice",
            "description": "Presence of Test",
            "values": [
                {"name": "absent", "description": "Test is not visible"},
                {"name": "present", "description": "Test is clearly visible"}
            ],
            "required": False,
            "max_selected": 1
        }
    ]
}, indent=2)

with patch("app.routers.drafts.helpers.add_ids_to_model", return_value=mock_model) as mock_add_ids:
    # Test code here
    # Inspect calls: mock_add_ids.call_args[1]["source"] for keyword arg
    #                mock_add_ids.call_args.args[1] for positional arg
```

**For `add_standard_codes_to_model`** - No-op mock:
```python
with patch("app.routers.drafts.helpers.add_standard_codes_to_model") as mock_add_codes:
    # No return value needed (mutates in place)
```

**For `asyncio.sleep`** - Instant execution:
```python
with patch("asyncio.sleep", new_callable=AsyncMock):
    # Instant execution, no actual delay
```

**For database** - Mock with Mock() pattern (like [`test_drafts_helpers.py:87-102`](tests/test_routers/test_drafts_helpers.py#L87-L102)):
```python
mock_database = Mock()
mock_database.finding_index = True  # or None for error test
mock_author = Mock()
mock_author.organization_code = "ACME"
mock_database.people.get.return_value = mock_author  # or None for fallback tests
```

### Test Decorator

All tests must use:
```python
@pytest.mark.asyncio
async def test_name():
```

## Success Criteria

1. ✅ All 6 tests pass
2. ✅ Tests are in new file `tests/test_routers/test_generate_finding_model_json.py`
3. ✅ Tests follow existing patterns in `tests/test_routers/test_drafts_helpers.py`
4. ✅ No changes to production code in `app/routers/drafts/helpers.py`
5. ✅ Tests execute quickly (<1s total) due to proper mocking
6. ✅ Coverage of `generate_finding_model_json` increases to >80%

## Notes

- **Don't test real AI generation**: The `create_model_from_markdown()` path is integration-tested
- **Focus on business logic**: Mock generation structure, source selection, name padding
- **Keep tests fast**: Mock `asyncio.sleep`, don't make real API/DB calls
- **Let validation run**: Don't mock `FindingModelBase.model_validate()` in tests 1-2 so we verify our mock structure is valid

## Related Files

- Function under test: [`app/routers/drafts/helpers.py:274-360`](app/routers/drafts/helpers.py#L274-L360)
- Existing helper tests: [`tests/test_routers/test_drafts_helpers.py`](tests/test_routers/test_drafts_helpers.py)
- Integration tests: [`tests/test_routers/test_drafts.py`](tests/test_routers/test_drafts.py)
