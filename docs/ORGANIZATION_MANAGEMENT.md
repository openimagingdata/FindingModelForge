# Organization Management Examples

## Updating User Organizations

Organizations are now managed as a simple list of strings through the user profile update endpoint.

### Example API Calls

#### Get current user profile

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/users/profile
```

#### Update user organizations

```bash
curl -X PATCH \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"organizations": ["ACR", "RSNA", "SIIM"]}' \
     http://localhost:8000/api/users/profile
```

#### Update other user fields along with organizations

```bash
curl -X PATCH \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "Updated Name",
       "email": "new-email@example.com",
       "organizations": ["ACR", "HIMSS"]
     }' \
     http://localhost:8000/api/users/profile
```

#### Get members of an organization (if you're a member)

```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
     http://localhost:8000/api/users/organizations/ACR/members
```

## Organization Code Rules

- Must be 3-4 uppercase letters
- Examples: `ACR`, `RSNA`, `SIIM`, `HIMSS`, `IEEE`
- Invalid: `acr` (lowercase), `ABC123` (contains numbers), `TOOLONG` (too long)

## Frontend Integration

```javascript
// Update user organizations
async function updateUserOrganizations(newOrganizations) {
  const response = await fetch('/api/users/profile', {
    method: 'PATCH',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      organizations: newOrganizations
    })
  });

  return response.json();
}

// Example usage
await updateUserOrganizations(['ACR', 'RSNA', 'SIIM']);
```
