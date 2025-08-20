# Database Documentation - FindingModelForge

## Overview

FindingModelForge uses MongoDB as its primary data store with an async Motor driver. The database contains collections
for users, finding model drafts, organizations, and other application data.

## Database Access via MCP

The MongoDB MCP server provides direct database access for development, testing, and administration tasks.

### Connecting to the Database

```bash
# Connect to local MongoDB instance
claude mcp add mongodb-local -- npx -y @mongodb-js/mcp-server

# Or if already configured, connect within Claude Code
# The MCP server will prompt for connection details
```

Within Claude Code, use the MongoDB MCP functions:

```python
# Connect to local development database
mcp__mongodb__connect("mongodb://localhost:27017")

# List all databases
mcp__mongodb__list-databases()

# Use the main application database
mcp__mongodb__list-collections("findingmodels")
```

## Database Schema

### Primary Database: `findingmodels`

The main application database containing all production collections.

#### Collections Overview

| Collection             | Purpose                    | Documents | Key Fields                              |
| ---------------------- | -------------------------- | --------- | --------------------------------------- |
| `users`                | User accounts and profiles | ~2-10     | id, login, email, organizations         |
| `finding_model_drafts` | Draft finding models       | ~4-20     | user_id, name, status, inputs           |
| `organizations_main`   | Organization data          | ~6-20     | name, members, settings                 |
| `people_main`          | Person entities            | Variable  | name, affiliations, contact             |
| `index_entries_main`   | Search/index data          | Variable  | terms, references, metadata             |
| `drafts`               | Legacy draft data          | Variable  | (deprecated - use finding_model_drafts) |
| `temp_drafts`          | Temporary draft storage    | Variable  | (temporary - cleanup regularly)         |

## Collection Schemas

### users

User accounts with GitHub OAuth integration.

```javascript
{
  _id: ObjectId,
  id: Number,                    // GitHub user ID (primary identifier)
  login: String,                 // GitHub username
  name: String,                  // Display name
  email: String,                 // Primary email
  avatar_url: String,            // GitHub avatar URL
  html_url: String | null,       // GitHub profile URL
  organizations: [String],       // Array of organization IDs
  is_active: Boolean,            // Account status
  created_at: Date,              // Account creation
  updated_at: Date               // Last profile update
}
```

**Key Patterns:**

- `id` field is the GitHub user ID, used for relationships
- `login` is unique GitHub username
- `organizations` array links to organization membership
- OAuth data synced from GitHub periodically

**Common Queries:**

```javascript
// Find user by GitHub ID
{ "id": 12345 }

// Find active users in organization
{ "is_active": true, "organizations": "medical-imaging" }

// Find user by email
{ "email": "user@example.com" }
```

### finding_model_drafts

Draft finding models with complete lifecycle management.

```javascript
{
  _id: ObjectId,
  user_id: Number,               // References users.id
  name: String,                  // Finding model name (case-insensitive unique per user)
  status: "draft" | "submitted", // Current status
  created_at: Date,              // Draft creation time
  updated_at: Date,              // Last modification time
  inputs: {                      // User input data
    description: String,         // Finding description (10-1000 chars)
    synonyms: [String],          // Alternative terms
    attributes_markdown: String  // Attributes in markdown (20+ chars)
  },
  generated_json: String | null, // AI-generated JSON output
  action_log: [{                 // Audit trail
    timestamp: Date,
    user_id: Number,
    action: String,              // "draft.created", "draft.saved", "status.changed"
    details: {                   // Action-specific data
      step?: String,             // Workflow step
      from_status?: String,      // Previous status
      to_status?: String         // New status
    } | null
  }]
}
```

**Key Patterns:**

- **Unique constraint**: One editable draft per (user_id, name, status='draft')
- **Status workflow**: draft → submitted (no reverse)
- **Action logging**: Complete audit trail for all operations
- **Input validation**: Description (10-1000), attributes (20+), synonyms array

**Common Queries:**

```javascript
// Find user's editable draft by name (case-insensitive)
{
  "user_id": 12345,
  "name": { "$regex": "^finding name$", "$options": "i" },
  "status": "draft"
}

// List all drafts for user
{ "user_id": 12345 }

// Find submitted models
{ "status": "submitted" }

// Find drafts with generated JSON
{ "generated_json": { "$ne": null } }
```

### organizations_main

Organization and group management.

```javascript
{
  _id: ObjectId,
  name: String,                  // Organization name
  display_name: String,          // Human-readable name
  description: String,           // Organization description
  members: [Number],             // Array of user IDs
  settings: {                    // Organization configuration
    visibility: "public" | "private",
    permissions: Object,
    features: [String]
  },
  created_at: Date,
  updated_at: Date
}
```

### people_main

Person entities and contact information.

```javascript
{
  _id: ObjectId,
  name: String,                  // Full name
  email: String,                 // Primary contact email
  affiliations: [String],        // Organizations/institutions
  roles: [String],               // Professional roles
  contact_info: {
    phone?: String,
    address?: Object,
    social?: Object
  },
  metadata: Object,              // Additional structured data
  created_at: Date,
  updated_at: Date
}
```

### index_entries_main

Search indexing and metadata.

```javascript
{
  _id: ObjectId,
  term: String,                  // Indexed term
  category: String,              // Term category
  references: [{                 // References to other documents
    collection: String,
    document_id: ObjectId,
    relevance_score: Number
  }],
  metadata: Object,              // Term metadata
  created_at: Date,
  updated_at: Date
}
```

## Database Operations via MCP

### Connection Management

```python
# Connect to database
mcp__mongodb__connect("mongodb://localhost:27017")

# List available databases
mcp__mongodb__list-databases()

# List collections in database
mcp__mongodb__list-collections("findingmodels")
```

### Data Querying

```python
# Count documents
mcp__mongodb__count("findingmodels", "users")
mcp__mongodb__count("findingmodels", "finding_model_drafts", {"status": "draft"})

# Find documents
mcp__mongodb__find("findingmodels", "users", {"is_active": true}, limit=10)
mcp__mongodb__find("findingmodels", "finding_model_drafts",
                   {"user_id": 12345}, limit=5, sort={"updated_at": -1})

# Get collection schema
mcp__mongodb__collection-schema("findingmodels", "finding_model_drafts")
```

### Data Modification

```python
# Insert single or multiple documents
mcp__mongodb__insert-many("findingmodels", "users", [
  {
    "id": 99999,
    "login": "test_user",
    "name": "Test User",
    "email": "test@example.com",
    "avatar_url": "https://example.com/avatar.png",
    "organizations": [],
    "is_active": true,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
])

# Update documents
mcp__mongodb__update-many("findingmodels", "users",
                          {"is_active": false},
                          {"$set": {"updated_at": "2024-12-19T10:00:00Z"}})

# Delete documents
mcp__mongodb__delete-many("findingmodels", "temp_drafts", {"created_at": {"$lt": "2024-01-01T00:00:00Z"}})
```

### Administrative Operations

```python
# Database statistics
mcp__mongodb__db-stats("findingmodels")

# Collection storage size
mcp__mongodb__collection-storage-size("findingmodels", "finding_model_drafts")

# Index management
mcp__mongodb__collection-indexes("findingmodels", "finding_model_drafts")
mcp__mongodb__create-index("findingmodels", "users", {"email": 1}, "email_unique")

# Query performance analysis
mcp__mongodb__explain("findingmodels", "finding_model_drafts",
                      [{"name": "find", "arguments": {"filter": {"user_id": 12345}}}])
```

## Development Database Setup

### Local Development

```bash
# Start MongoDB locally (Docker)
docker run -d -p 27017:27017 --name mongodb mongo:latest

# Or use docker-compose (if available in project)
docker-compose up -d mongodb
```

### Environment Configuration

```env
# .env file
MONGODB_URI="mongodb://localhost:27017"
MONGODB_DB="findingmodels"
```

### Sample Data

The development database includes:

- 2+ test users with GitHub OAuth data
- 4+ draft finding models in various states
- 6+ organizations for testing membership
- Supporting collections with realistic data

## Data Validation Rules

### Finding Model Drafts

- **Name**: 3-200 characters, case-insensitive unique per user
- **Description**: 10-1000 characters required
- **Attributes**: 20+ characters required for submission
- **Synonyms**: Array of strings, no duplicates
- **Status**: Only "draft" → "submitted" transitions allowed

### Users

- **ID**: Must be positive integer (GitHub user ID)
- **Login**: Required, GitHub username format
- **Email**: Required, valid email format
- **Organizations**: Array of valid organization identifiers

## Performance Considerations

### Indexes

The application uses these indexes for performance:

```javascript
// Users collection
{ "id": 1 }                    // Unique GitHub user ID
{ "email": 1 }                 // Email lookup
{ "login": 1 }                 // Username lookup

// Finding model drafts collection
{ "user_id": 1, "name": 1, "status": 1 }  // Compound for draft uniqueness
{ "user_id": 1, "updated_at": -1 }        // User draft listing
{ "status": 1 }                           // Status queries
```

### Query Patterns

- **Always filter by user_id** for user-scoped operations
- **Use case-insensitive regex** for name lookups: `{"$regex": "^name$", "$options": "i"}`
- **Sort by updated_at** for chronological listing
- **Limit results** for pagination and performance

## Backup and Maintenance

### Regular Maintenance

```python
# Clean up temporary drafts older than 7 days
mcp__mongodb__delete-many("findingmodels", "temp_drafts",
                          {"created_at": {"$lt": "2024-12-12T00:00:00Z"}})

# Update user activity status
mcp__mongodb__update-many("findingmodels", "users",
                          {"updated_at": {"$lt": "2024-06-01T00:00:00Z"}},
                          {"$set": {"is_active": false}})
```

### Database Health Checks

```python
# Check collection sizes
mcp__mongodb__collection-storage-size("findingmodels", "finding_model_drafts")

# Verify data integrity
mcp__mongodb__count("findingmodels", "finding_model_drafts", {"status": {"$in": ["draft", "submitted"]}})

# Performance monitoring
mcp__mongodb__db-stats("findingmodels")
```

## Security Considerations

- **Connection strings**: Never commit credentials to version control
- **User isolation**: All queries must include user_id for user-scoped data
- **Input validation**: Validate all data before database operations
- **Index security**: Ensure indexes support security queries efficiently

## Troubleshooting

### Common Issues

1. **Connection failures**: Verify MongoDB is running and connection string is correct
2. **Permission errors**: Check user_id filtering in queries
3. **Duplicate key errors**: Verify unique constraints (user_id + name + status)
4. **Performance issues**: Check query plans with `explain()` operations

### Debug Queries

```python
# Find drafts without proper user isolation
mcp__mongodb__find("findingmodels", "finding_model_drafts", {"user_id": {"$exists": false}})

# Check for invalid statuses
mcp__mongodb__find("findingmodels", "finding_model_drafts", {"status": {"$nin": ["draft", "submitted"]}})

# Find orphaned drafts (users that don't exist)
mcp__mongodb__aggregate("findingmodels", "finding_model_drafts", [
  {"$lookup": {"from": "users", "localField": "user_id", "foreignField": "id", "as": "user"}},
  {"$match": {"user": {"$size": 0}}}
])
```

## Related Documentation

- [Backend Development Guide](../app/CLAUDE.md) - Application code patterns
- [Testing Documentation](../tests/CLAUDE.md) - Database testing patterns
- [Draft Management](../CHANGELOG.md) - Draft system implementation details

---

For development and testing, use the MongoDB MCP server to interact with the database directly through Claude Code. This
provides full access to all MongoDB operations while maintaining proper data relationships and constraints.
