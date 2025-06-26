# User Management Improvements

## Overview

The User handling system has been significantly improved with the following changes:

## Key Changes

### 1. Simplified User ID System

- **GitHub ID as Primary Key**: Users now use their GitHub ID directly as their primary ID in our system
- **No Separate ID**: Removed the need for a separate `github_id` field
- **GitHub Username**: Added `login` field to store the GitHub username

### 2. Enhanced User Profile Management

- **Updatable Fields**: Users can update their email, avatar URL, and HTML URL
- **Organization Support**: Users can associate with multiple organizations identified by 3-4 uppercase letter codes

### 3. MongoDB Integration

- **Async Database**: Using Motor library for async MongoDB operations
- **Environment Configuration**: `MONGODB_URI` and `MONGODB_DB` environment variables
- **Database Connection**: Initialized at app startup with proper connection management

### 4. Repository Pattern

- **UserRepo Class**: Centralized database operations for user management
- **Dependency Injection**: Clean separation of concerns with dependency injection
- **Async Operations**: All database operations are async for better performance

## Models

### User Model

```python
class User(UserBase):
    """User model with database fields."""
    id: int  # GitHub ID as primary key
    is_active: bool = True
    organizations: list[str] = Field(default_factory=list)  # 3-4 letter org codes
    created_at: datetime
    updated_at: datetime
```

### UserUpdate Model

```python
class UserUpdate(BaseModel):
    """User update model."""
    name: str | None = None
    email: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    organizations: list[str] | None = None
```

## API Endpoints

### User Profile Management

- `GET /api/users/profile` - Get current user's profile
- `PATCH /api/users/profile` - Update user profile (including organizations)

### Organization Management

- `GET /api/users/organizations/{org_code}/members` - Get organization members

## Database Operations

### UserRepo Methods

- `create_user(user_data: UserCreate)` - Create a new user
- `get_user(user_id: int)` - Get user by GitHub ID
- `get_user_by_login(login: str)` - Get user by GitHub username
- `update_user(user_id: int, user_update: UserUpdate)` - Update user information
- `list_users_by_organization(org_code: str)` - Get all users in an organization

## Managing Organizations

Organizations are managed through the user profile update endpoint. Users can update their organization memberships by sending a PATCH request to `/api/users/profile` with the organizations field:

```json
{
  "organizations": ["ACR", "RSNA", "SIIM"]
}
```

This will replace the user's current organization list with the new one. To add an organization, include it in the list. To remove an organization, exclude it from the list.

## Environment Variables

Add these to your `.env` file:

```bash
# MongoDB Configuration
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=findingmodels
```

## Organization Codes

Organization codes must be:

- 3-4 characters long
- Uppercase letters only
- Examples: `ACR`, `RSNA`, `SIIM`, `HIMSS`

## Migration Notes

If you have existing data:

1. Update existing user records to use GitHub ID as primary key
2. Add `organizations` field as empty array
3. Ensure all user records have `created_at` and `updated_at` timestamps
