# Claude Code Instructions for FindingModelForge

# ⚠️ CRITICAL UI REMINDERS ⚠️

**ALWAYS use Flowbite components and patterns. Do NOT create custom CSS classes or JavaScript.** **ALWAYS use Alpine.js
for interactivity. Do NOT write ad hoc JavaScript.**

## Before writing ANY UI code:

1. ✅ Check https://flowbite.com/docs/components/ FIRST
2. ✅ Use their exact HTML structure and CSS classes
3. ✅ Use Alpine.js `x-data`, `x-model`, computed properties for reactivity
4. ✅ Never deviate from established patterns without explicit approval
5. ❌ Do NOT create custom validation, modal, or interaction code

## Project Overview

FindingModelForge is a FastAPI-based web application for creating and managing medical imaging finding models. These
models define semantic labels and structured attributes for medical imaging findings, using the `findingmodel` library
for core functionality.

**Current Branch**: `dev` (main branch: `main`)

## Technical Stack

### Backend

- **FastAPI** (0.115.0+) - Async web framework with automatic API documentation
- **Python 3.12+** - With extensive type hinting throughout
- **Pydantic** - Data validation for models, API contracts, and config
- **Motor** - Async MongoDB driver for data persistence
- **Redis** - Optional caching layer (configurable via env)
- **JWT + GitHub OAuth** - Authentication system with HTTP-only cookies
- **Loguru** - Structured logging framework

### Frontend

- **Jinja2** - Server-side templating with component macros
- **Tailwind CSS v4** - Utility-first CSS with dark mode support
- **Alpine.js** - Reactive JavaScript for interactivity
- **Flowbite** - Pre-built UI components (data-attribute driven)
- **Vite** - Modern frontend build system with hot reload

### Core Domain Library

- **findingmodel** (0.3.1+) - Core library for finding model operations
  - Provides `FindingInfo`, `Index`, `Person`, `Organization` models
  - Tools for AI-powered model generation and similarity detection

## Project Structure

```
/Users/talkasab/Repos/FindingModelForge/
├── app/                      # FastAPI application
│   ├── main.py              # Application factory and lifespan
│   ├── auth.py              # JWT and OAuth implementation
│   ├── cache.py             # Redis cache abstraction
│   ├── config.py            # Pydantic settings management
│   ├── database.py          # MongoDB connection and repositories
│   ├── dependencies.py      # FastAPI dependency injection
│   ├── models.py            # Pydantic data models
│   ├── health.py            # Health check endpoints
│   ├── vite_manifest.py     # Vite asset management
│   └── routers/
│       ├── auth.py          # Authentication routes
│       ├── finding_models.py # Finding model CRUD operations
│       ├── pages.py         # HTML page rendering
│       ├── static.py        # Static file serving
│       └── users.py         # User management
├── templates/               # Jinja2 templates
│   ├── base.html           # Base template with Tailwind/Alpine
│   ├── components/         # Reusable UI components
│   │   ├── finding_model_complete_display.html  # Full model display + JSON
│   │   ├── finding_model_display.html           # Basic model display
│   │   └── finding_model_creation/              # Multi-step creation workflow
│   ├── macros/             # Jinja2 macros for components
│   │   ├── json_accordion.html         # Flowbite JSON accordion
│   │   ├── form_validation.html        # Alpine.js form validation
│   │   ├── synonym_manager.html        # Interactive synonym management
│   │   ├── app_components.html         # General app components
│   │   └── flowbite_components.html    # Flowbite component wrappers
│   └── *.html              # Page templates
├── static/                 # Static assets
│   ├── css/               # Compiled Tailwind CSS
│   ├── js/                # Vite-built JavaScript
│   └── images/            # Icons and images
├── src/                   # Frontend source files
│   ├── input.css         # Tailwind input file
│   └── js/main.js        # JavaScript entry point
├── tests/                 # Pytest test suite
├── docs/                  # Documentation
├── package.json          # Node dependencies (Tailwind, Vite, Alpine)
├── pyproject.toml        # Python dependencies and tool config
├── vite.config.js        # Vite configuration
├── Taskfile.yml          # Task runner definitions
└── docker-compose.yml    # Local development services

```

## Key Patterns & Conventions

### Type Safety

- **Always** use type hints for function signatures
- Use `Annotated` for FastAPI dependencies
- Prefer explicit types over `Any`
- Enable MyPy strict mode compliance

### Async Patterns

```python
# Always use async/await for I/O operations
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
        # Cache for next time
        await cache.set(f"model:{model_id}", doc.model_dump_json())
        return FindingModel.model_validate(doc)

    return None
```

### Dependency Injection

```python
# Use FastAPI's dependency system
from app.dependencies import DatabaseDep, CacheDep, CurrentUserDep

@router.post("/create")
async def create_model(
    request: FindingModelRequest,
    current_user: CurrentUserDep,  # Auto-injected auth user
    database: DatabaseDep,          # Auto-injected database
    cache: CacheDep,                # Auto-injected cache
) -> FindingModel:
    ...
```

### Frontend Components

**CRITICAL: Use Flowbite's data-attribute patterns, NOT custom JavaScript** **CRITICAL: Use Alpine.js low-impact
patterns, NOT ad hoc JavaScript**

## UI Development Process (MANDATORY):

1. **Check Flowbite docs FIRST**: https://flowbite.com/docs/components/
2. **Copy exact HTML structure** from Flowbite examples
3. **Use their CSS classes verbatim** - Do NOT modify or create custom ones
4. **For interactivity**: Use Alpine.js `x-data`, `x-model`, computed getters
5. **For components**: Use Flowbite's data-attribute driven components

## Alpine.js Patterns (REQUIRED):

- ✅ Use `x-model` for two-way data binding
- ✅ Use computed properties (`get propertyName()`) for reactive logic
- ✅ Use simple data objects, not complex validation frameworks
- ✅ Let Alpine handle DOM updates automatically
- ❌ Do NOT write manual DOM manipulation
- ❌ Do NOT create custom event handlers beyond Alpine patterns

```html
<!-- ✅ CORRECT: Official Flowbite stepper from docs -->
<ol class="flex items-center w-full text-sm font-medium text-center text-gray-500 dark:text-gray-400 sm:text-base">
  <li
    class="flex md:w-full items-center text-blue-600 dark:text-blue-500 sm:after:content-[''] after:w-full after:h-1 after:border-b after:border-gray-200 after:border-1 after:hidden sm:after:inline-block after:mx-6 xl:after:mx-10 dark:after:border-gray-700"
  >
    <span class="flex items-center">
      <svg
        class="w-3.5 h-3.5 sm:w-4 sm:h-4 me-2.5"
        aria-hidden="true"
        xmlns="http://www.w3.org/2000/svg"
        fill="currentColor"
        viewBox="0 0 20 20"
      >
        <path
          d="M10 .5a9.5 9.5 0 1 0 9.5 9.5A9.51 9.51 0 0 0 10 .5Zm3.707 8.207-4 4a1 1 0 0 1-1.414 0l-2-2a1 1 0 0 1 1.414-1.414L9 10.586l3.293-3.293a1 1 0 0 1 1.414 1.414Z"
        />
      </svg>
      Personal Info
    </span>
  </li>
</ol>

<!-- ❌ WRONG: Made-up custom styling -->
<div class="w-5 h-5 bg-blue-600 rounded-full">1</div>

<!-- ✅ CORRECT: Flowbite accordion from docs -->
<div data-accordion="collapse">
  <h2 id="accordion-heading-1">
    <button
      type="button"
      data-accordion-target="#accordion-body-1"
      aria-expanded="false"
      aria-controls="accordion-body-1"
    >
      Toggle Section
    </button>
  </h2>
  <div id="accordion-body-1" class="hidden" aria-labelledby="accordion-heading-1">Content here</div>
</div>

<!-- ❌ WRONG: Custom implementation -->
<button onclick="toggleSection()">Toggle</button>
```

**Before implementing any component:**

1. Visit https://flowbite.com/docs/components/
2. Find the exact component you need
3. Copy the official HTML structure and CSS classes
4. Adapt only the content, not the structure or styling

### Alpine.js and HTMX Integration Patterns

**CRITICAL: Trust Alpine.js reactivity - avoid manual DOM manipulation**

#### ✅ CORRECT: Reactive Data Binding for Forms

```javascript
// Use computed getters for derived data
x-data='{
  items: ["item1", "item2"],
  get itemsJson() { return JSON.stringify(this.items); }
}'

// Use x-model for form submission (updates DOM value property)
<input type="hidden" name="items" x-model="itemsJson">
```

#### ❌ WRONG: Manual HTMX Event Handling

```javascript
// Don't manually update form data in HTMX events
@htmx:config-request="$event.detail.parameters.items = JSON.stringify(items)"
@htmx:before-request="updateFormData()"
```

#### Key Principles:

1. **x-model vs :value**:
   - `x-model` updates DOM value property (form submission)
   - `:value` only sets HTML attribute (not submitted)

2. **Computed Properties**: Use JavaScript getters for automatic updates

   ```javascript
   get "derivedValue"() { return this.sourceValue.toUpperCase(); }
   ```

3. **Form Scope**: Put `x-data` on form element when form needs access to data

4. **Event Handling**: Use `.stop.prevent` modifiers to control event flow

   ```html
   @click.stop.prevent="handleClick()"
   ```

5. **HTMX Integration**: Alpine.js reactivity handles form data automatically - no HTMX event interception needed

#### Component Reusability Pattern:

```jinja
{# templates/macros/component_name.html #}
{% macro component_data(initial_data) %}
{
  "data": {{ initial_data | tojson }},
  get "dataJson"() { return JSON.stringify(this.data); },
  "addItem": function(item) { this.data.push(item); }
}
{% endmacro %}

{% macro component_template() %}
<div>
  <!-- Component HTML with Alpine.js directives -->
  <input type="hidden" name="data" x-model="dataJson">
</div>
{% endmacro %}
```

### Template Component Reuse

**CRITICAL: Always check for existing components before creating new display code**

1. **Audit existing components first** - Search templates/ directory for similar functionality
2. **Reuse existing templates** - Use `{% include %}` for complete template reuse
3. **Extract common patterns** - Create shared macros for repeated UI patterns
4. **Maintain component index** - Keep track of available reusable components

**Component Discovery Process:**

```bash
# Search for existing display components
find templates/ -name "*.html" | grep -E "(display|card|list)"
# Search for specific functionality
grep -r "accordion" templates/
grep -r "badge" templates/macros/
```

**Reuse Patterns:**

```jinja
{# ✅ CORRECT: Reuse existing component #}
{% set finding_model = session_data.final_model %}
{% include 'components/finding_model_display.html' %}

{# ✅ CORRECT: Use existing macros #}
{% from "macros/flowbite_components.html" import alert, badge %}
{{ alert("Success message", type="success") }}
{{ badge("Status", "green") }}

{# ❌ WRONG: Recreating existing functionality #}
<div class="bg-green-100 text-green-800 px-3 py-1 rounded">
    Success message
</div>
```

**Available Component Index:**

- `components/finding_model_display.html` - Complete finding model display with attributes
- `components/finding_model_creation/` - Multi-step creation workflow components
- `macros/flowbite_components.html` - Flowbite UI component macros
- `macros/app_components.html` - Application-specific component macros
- `macros/synonym_manager.html` - Synonym management component (Alpine.js + HTMX)

**Before creating new display code:**

1. Check if a similar component exists in `templates/components/`
2. Check if relevant macros exist in `templates/macros/`
3. Consider if existing components can be extended/adapted
4. Only create new components if truly needed
5. Extract reusable parts into macros for future use

### Jinja2 Macros

```jinja
{# Use macros for reusable components #}
{% from "macros/app_components.html" import render_finding_model %}

{{ render_finding_model(model_data) }}
```

## Reusable Components & Macros

The application uses a component-based architecture with reusable Jinja2 macros and templates for consistency and
maintainability.

### Finding Model Display Components

**Complete Display Component**

- **File**: `templates/components/finding_model_complete_display.html`
- **Purpose**: Full finding model display with formatted view + JSON accordion
- **Usage**: Use everywhere finding models need to be displayed

```jinja
{% include 'components/finding_model_complete_display.html' %}
```

**Basic Display Component**

- **File**: `templates/components/finding_model_display.html`
- **Purpose**: Formatted finding model display only (no JSON)
- **Usage**: When you only need the visual display without JSON export

```jinja
{% include 'components/finding_model_display.html' %}
```

### JSON Accordion Macro

**File**: `templates/macros/json_accordion.html`

- **Purpose**: Proper Flowbite accordion with JSON display, copy, and download functionality
- **Features**: Dynamic rounded corners, hover effects, proper Flowbite styling
- **Usage**:

```jinja
{% from 'macros/json_accordion.html' import json_accordion %}
{{ json_accordion(finding_model, "unique-id", "Custom Title") }}
```

### Form Validation Macros

**File**: `templates/macros/form_validation.html`

- **Purpose**: Alpine.js form validation with computed properties
- **Features**: Reactive validation, field-specific checks, form state management
- **Usage**:

```jinja
{% from 'macros/form_validation.html' import validation_data, validated_input, validated_textarea %}

<div x-data='{{ validation_data(initial_name="", initial_description="") }}'>
  {{ validated_input("name", "Finding Name", minlength=3, maxlength=200) }}
  {{ validated_textarea("description", "Description", rows=4, required=true) }}
</div>
```

### Synonym Management Macro

**File**: `templates/macros/synonym_manager.html`

- **Purpose**: Interactive synonym add/remove with Alpine.js
- **Features**: Visual badges, add/remove functionality, JSON serialization for forms
- **Usage**:

```jinja
{% from 'macros/synonym_manager.html' import synonym_manager, synonym_data %}

<div x-data='{{ synonym_data(initial_synonyms) }}'>
  {{ synonym_manager() }}
</div>
```

### Component Guidelines

1. **Always use existing components** before creating new ones
2. **Follow Flowbite patterns exactly** - no custom styling
3. **Use Alpine.js reactively** with `x-model`, computed properties, and minimal JavaScript
4. **Macro parameters should be intuitive** and well-documented
5. **Components must be responsive** and support dark mode
6. **Include accessibility attributes** (ARIA, semantic HTML)

### Creating New Components

When creating new reusable components:

1. **Check existing macros first** - extend rather than duplicate
2. **Use Flowbite documentation** as the source of truth for HTML structure
3. **Place in appropriate directory**:
   - `templates/components/` - Full page sections or complex components
   - `templates/macros/` - Simple, parameterized macros
4. **Document parameters and usage** with Jinja comments
5. **Test with different data** and edge cases
6. **Ensure proper error handling** for missing or invalid data

Example new macro structure:

```jinja
{# Purpose: Brief description of what this macro does #}
{# Parameters:
   - param1: Description of parameter 1
   - param2: Description of parameter 2 (optional, defaults to "value")
#}
{% macro my_component(param1, param2="default") %}
  <!-- Flowbite-compliant HTML structure -->
  <div class="exact-flowbite-classes">
    {{ param1 }}
  </div>
{% endmacro %}
```

## HTMX Multi-Step Workflow Patterns

The finding model creation workflow demonstrates best practices for HTMX-driven multi-step forms.

### Session Management

**Server-side session storage** with Redis caching:

```python
# In app/dependencies.py
@dataclass
class FindingModelCreationSession:
    session_id: str
    current_step: int = 1
    name: str | None = None
    description: str | None = None
    synonyms: list[str] = field(default_factory=list)
    # ... other fields
```

**Session dependency injection**:

```python
async def get_creation_session(
    session_id: str = Form(default=""),
    session_manager: SessionManagerDep = Depends(get_session_manager)
) -> FindingModelCreationSession:
    # Automatic session creation/retrieval
```

### Step Template Consolidation

**Single helper function** for rendering all steps:

```python
def render_step_template(
    request: Request,
    step_number: int,
    session: FindingModelCreationSession,
    **extra_context: Any
) -> str:
    step_templates = {
        1: "components/finding_model_creation/step_1_enter_name.html",
        2: "components/finding_model_creation/step_2_edit_description.html",
        # ... etc
    }
    context = {"request": request, "current_step": step_number, "session_data": session, **extra_context}
    return templates.get_template(step_templates[step_number]).render(**context)
```

### Form Validation Patterns

**FastAPI Form validation**:

```python
@router.post("/create/step/1")
async def process_step_1(
    name: str = Form(min_length=3, max_length=200),  # Built-in validation
    session: CreationSessionDep,
) -> HTMLResponse:
    # Validation errors automatically return 422
```

**Manual validation with proper error handling**:

```python
def parse_synonyms(synonyms: str) -> list[str]:
    if not synonyms.strip():
        return []
    try:
        parsed = json.loads(synonyms)
        if not isinstance(parsed, list):
            raise ValueError("Must be a JSON array")
        return [s.strip() for s in parsed if isinstance(s, str) and s.strip()]
    except (json.JSONDecodeError, ValueError) as e:
        raise HTTPException(status_code=422, detail=f"Invalid format: {str(e)}")
```

### HTMX Integration

**Automatic component reinitialization**:

```javascript
// In src/js/main.js
document.addEventListener("htmx:afterSwap", function (event) {
  initFlowbite() // Reinitialize Flowbite components
  if (window.Alpine && event.detail.elt) {
    Alpine.initTree(event.detail.elt) // Process new Alpine.js components
  }
})
```

**Template structure for HTMX swapping**:

```html
<!-- Base template with swap target -->
<div id="step-container" class="max-w-4xl mx-auto">
  <!-- Step content gets swapped here -->
</div>

<!-- Step templates return just the content -->
<form hx-post="/api/step/2" hx-target="#step-container" hx-swap="innerHTML">
  <!-- Form content -->
</form>
```

## Development Workflow

### Environment Setup

```bash
# Install Python dependencies
uv sync --all-extras --dev

# Install Node dependencies and build frontend
npm install
npm run build

# Or use Task runner
task setup
```

### Running Development Server

```bash
# With hot reload
task dev

# With CSS watching
task dev-watch

# Manual
uv run uvicorn app.main:app --reload
```

### Code Quality

```bash
# Format and lint
task lint
# or
uv run ruff format .
uv run ruff check --fix .

# Type checking
task typecheck
# or
uv run mypy app

# Run tests
task test
# or
uv run pytest
```

### Frontend Development

```bash
# Build CSS
npm run build:css

# Watch CSS changes
npm run watch:css

# Build JavaScript with Vite
npm run build:js

# Full frontend build
task build-frontend
```

## Environment Configuration

Required `.env` file:

```env
# Application
APP_NAME="FindingModelForge"
DEBUG=true
ENVIRONMENT=development

# Security
SECRET_KEY="your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# GitHub OAuth
GITHUB_CLIENT_ID="your-client-id"
GITHUB_CLIENT_SECRET="your-client-secret"

# MongoDB
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB="findingmodelforge"

# Redis (optional)
REDIS_ENABLED=true
REDIS_HOST="localhost"
REDIS_PORT=6379
REDIS_DB=0

# Server
HOST="0.0.0.0"
PORT=8000
```

## Finding Model Domain

The application works with medical imaging finding models that have:

- **Name**: Primary identifier for the finding
- **Description**: Clinical description
- **Synonyms**: Alternative names
- **Attributes**: Structured properties with controlled vocabularies
- **Tags**: Categorization metadata

### Key Operations

1. **Check Name Availability** - Verify uniqueness in index
2. **Generate Finding Info** - AI-powered description/synonym generation
3. **Find Similar Models** - Detect potential duplicates
4. **Create Model** - Generate complete model with attributes
5. **Index Management** - Store and retrieve models from MongoDB

## Common Tasks

### Adding a New API Endpoint

1. Define Pydantic models in `app/models.py`
2. Create route handler in appropriate router
3. Use dependency injection for database/cache/auth
4. Add tests in `tests/`
5. Update API documentation if needed

### Adding a New Page

1. Create template in `templates/`
2. Use Flowbite components and Alpine.js
3. Add route in `app/routers/pages.py`
4. Style with Tailwind utilities
5. Test authentication if protected

### Working with the Database

```python
# In app/database.py or repositories
async def create_finding_model(
    self,
    model_data: FindingModelCreate
) -> FindingModel:
    doc = model_data.model_dump()
    doc["created_at"] = datetime.now(UTC)

    result = await self.collection.insert_one(doc)
    doc["_id"] = result.inserted_id

    return FindingModel.model_validate(doc)
```

### Using the Cache

```python
# Cache operations are optional (check if enabled)
if cache and await cache.is_healthy():
    await cache.set(
        key="model:123",
        value=model.model_dump_json(),
        ttl=3600  # 1 hour
    )
```

## Testing

### Test Organization

Tests are organized into **unit tests** and **integration tests**:

- **Unit tests**: Fast tests that mock external dependencies (71 tests, ~0.4s)
- **Integration tests**: Tests that involve external systems like GitHub API, MongoDB, Redis (35 tests, ~0.15s)

### Running Tests

```bash
# All tests with coverage
task test

# Fast unit tests only (recommended for development)
task test-unit

# Integration tests only (for CI/deployment verification)
task test-integration

# Full test suite with quality checks
task test-full

# Using pytest directly
uv run pytest -m "not integration" -v      # Unit tests
uv run pytest -m "integration" -v          # Integration tests
uv run pytest tests/test_auth.py -v        # Specific test file
uv run pytest --cov=app --cov-report=term-missing  # With coverage
```

### Test Structure

- **Unit tests**: Mock external dependencies, test business logic in isolation
- **Integration tests**: Test full workflows including database operations, OAuth flows
- Marked with `@pytest.mark.integration` or `pytestmark = pytest.mark.integration`
- Async test patterns with `pytest-asyncio`
- Comprehensive coverage: 79% overall, 96% database layer, 75% auth layer

## Docker & Deployment

### Local Development

```bash
# Start MongoDB and Redis
docker-compose up -d

# Build application image
task build

# Run in container
task run-container
```

### Production Considerations

- Set strong `SECRET_KEY`
- Configure production MongoDB URI
- Enable Redis for caching
- Set `DEBUG=false`
- Configure proper CORS origins
- Use HTTPS termination

## Important Guidelines

1. **Type Safety**: Always include type hints
2. **Async First**: Use async/await for all I/O
3. **Error Handling**: Proper exception handling with HTTPException
4. **Logging**: Use Loguru with appropriate levels
5. **UI Components**: ⚠️ **CRITICAL** - Use Flowbite's exact patterns from docs, NO custom CSS/JS
6. **Alpine.js**: ⚠️ **CRITICAL** - Use `x-model`, computed properties, NO ad hoc JavaScript
7. **Testing**: Write tests for new features
8. **Security**: Never commit secrets, use env vars

## UI Development Rules (NON-NEGOTIABLE)

- ❌ **NEVER** create custom form validation logic
- ❌ **NEVER** write manual DOM manipulation
- ❌ **NEVER** deviate from Flowbite CSS classes
- ✅ **ALWAYS** check Flowbite docs before writing UI code
- ✅ **ALWAYS** use Alpine.js declarative patterns

## Debugging Tips

1. Check logs with Loguru output
2. Verify `.env` configuration
3. Run `task check` for code quality
4. For UI issues, ensure `initFlowbite()` is called
5. Check MongoDB connection status
6. Verify Redis cache if enabled

## Resources

- FastAPI Docs: https://fastapi.tiangolo.com
- Flowbite Components: https://flowbite.com/docs
- Alpine.js: https://alpinejs.dev
- Tailwind CSS: https://tailwindcss.com
- Finding Model Library: Internal `findingmodel` package

---

Remember: This is a medical domain application. Maintain high code quality, comprehensive testing, and proper error
handling throughout.
