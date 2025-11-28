# Future Enhancements

Potential features and improvements for future development. These are not bugs or technical debt, but ideas for
enhancing the application.

## Comment System Enhancements

Potential features to enhance the commenting system:

### Pagination for Large Threads

- Display comments in pages when thread has > 100 comments
- Infinite scroll or "Load more" button
- Maintain state when navigating away and back

### Rich Text/Markdown Editor

- Allow basic markdown in comments (bold, italic, links, code blocks)
- Live preview while typing
- Sanitize HTML output for security

### Email Notifications

- Notify users when someone replies to their comment
- Opt-in/opt-out preference in user profile
- Digest emails for multiple replies

### Sort Order Toggle

- Allow users to toggle between oldest-first and newest-first
- Persist preference in session/localStorage

### Comment Editing

- Allow users to edit their own comments
- Show edit history/timestamp
- Mark edited comments visually
- Time limit for edits (e.g., 15 minutes)

### Voting/Reactions

- Upvote/downvote comments
- Emoji reactions (👍 ❤️ 😄 etc.)
- Display vote counts
- Prevent self-voting

---

## Draft System Enhancements

### Draft Versioning

- Track multiple versions of draft edits
- Allow reverting to previous version
- Show diff between versions

### Collaborative Drafts

- Multiple users can co-author a draft
- Permission management (owner, editor, viewer)
- Track who made which changes

---

## Finding Models Enhancements

### Advanced Search

- Filter by attributes (modality, body part, etc.)
- Full-text search in descriptions
- Search by index codes

### Model Collections/Tags

- Allow users to create collections of models
- Tag models for organization
- Share collections with others

---

## Guidelines

**Adding enhancements:**

1. Describe the feature clearly
2. Note any dependencies or prerequisites
3. Consider UX and implementation complexity

**Prioritizing enhancements:**

- User requests and feedback should drive prioritization
- Consider technical complexity vs user value
- Look for quick wins (high value, low effort)

**Moving to implementation:**

1. Create detailed spec in `tasks/` folder
2. Break down into milestones
3. Update this file when started
