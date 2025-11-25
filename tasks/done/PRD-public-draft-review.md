# Product Requirements Document: Public Draft Review Feature

## Executive Summary

Introduce a new "public" state for finding model drafts that enables peer review and commenting before final submission.
This creates a collaborative review workflow similar to pull requests in code development.

## User Story

**As a** finding model author **I want to** make my draft publicly visible for review and feedback **So that** I can
improve my model based on peer input before final submission

**As a** finding model reviewer **I want to** view and comment on public drafts **So that** I can provide feedback and
help improve models before they're finalized

## Current State vs Proposed State

### Current Workflow

1. **Draft** (private, editable by author only)
2. **Submitted** (public, locked, no further edits)

### Proposed Workflow

1. **Draft** (private, editable by author only)
2. **Public** (visible to all, editable by author, commentable by others)
3. **Submitted** (public, locked, no further edits)

## Functional Requirements

### State Transitions

- Draft → Public (author action: "Make Public")
- Public → Submitted (author action: "Submit for Repository")
- Draft → Submitted (blocked - must go through public state first)

### Permissions Matrix

| State     | Author Can View | Author Can Edit | Others Can View | Others Can Edit | Others Can Comment |
| --------- | --------------- | --------------- | --------------- | --------------- | ------------------ |
| Draft     | ✅              | ✅              | ❌              | ❌              | ❌                 |
| Public    | ✅              | ✅              | ✅              | ❌              | ✅                 |
| Submitted | ✅              | ❌              | ✅              | ❌              | ✅                 |

### Core Features

#### 1. Making Drafts Public

- Add "Make Public" button on draft edit page
- Confirmation dialog explaining implications
- Status change to "public" in database
- Draft becomes visible in public listings

#### 2. Public Draft Discovery

- **NEW dedicated `/drafts` page** with table view
- Columns: Title, Author, Created, Last Activity, Comments
- Filter options: All / Public (Under Review) / My Drafts
- Sort by: Recent Activity (default) / Most Comments / Newest
- Status badges: "Under Review" vs "Draft" vs "Submitted"

#### 3. Commenting on Public Drafts

- Leverage existing comment system
- Comments persist through submission
- Thread organization for discussion topics
- Real-time updates via HTMX

#### 4. Author Controls

- Continue editing while public
- View all comments in context
- Respond to feedback
- Submit when ready (after public period)

## Technical Implementation

### Database Changes

```python
class DraftStatus(str, Enum):
    DRAFT = "draft"      # Private, editable
    PUBLIC = "public"    # Public review, still editable
    SUBMITTED = "submitted"  # Final, locked
```

### URL Structure

- `/drafts` - **NEW**: Table of all public drafts for review
- `/drafts/{id}` - Unified view (respects permissions)
- `/drafts/{id}/make-public` - Action endpoint
- `/finding-models` - Existing browse (shows only submitted models)

### API Endpoints

- `POST /drafts/{id}/make-public` - Change status to public
- `GET /api/drafts/public` - List all public drafts
- Existing comment endpoints work unchanged

### UI Components

- Status indicator badge (Draft/Under Review/Final)
- "Make Public" button with confirmation modal
- Public drafts section on browse page
- Comment count indicators

## Non-Functional Requirements

### Performance

- Cache public draft listings in Redis
- Pagination for comment threads
- Lazy load comments on scroll

### Security

- Strict ownership validation before status changes
- Rate limiting on status transitions
- Audit logging for all state changes

### User Experience

- Clear status indicators throughout UI
- Helpful tooltips explaining each state
- Progress indicator: Draft → Review → Final

## Design Decisions (Finalized)

### Resolved Decisions

1. **Reversibility**: ❌ **Not supported**
   - Once public, drafts cannot revert to private
   - Encourages authors to thoroughly prepare before making public
   - Simplifies state management and user expectations

2. **Minimum Review Period**: ❌ **No waiting period**
   - Authors can submit immediately after making public
   - Future enhancement: May require at least one comment before submission
   - Flexibility for urgent submissions

3. **Discovery**: ✅ **Dedicated drafts page**
   - New `/drafts` page with table of all public drafts
   - Sortable columns: Title, Author, Created, Last Activity, Comment Count
   - Filterable by status: All / Public (Under Review) / My Drafts
   - Clear visual distinction between public and private drafts

4. **Orphaned Drafts**: ✅ **30-day auto-archive**
   - Public drafts with no activity for 30 days move to archive collection
   - Archive maintains historical record but removes from active listings
   - Authors can still access archived drafts from profile
   - Prevents accumulation of abandoned reviews

5. **Access Control**: ✅ **All authenticated users**
   - Any logged-in user can view and comment on public drafts
   - Maintains consistency with current model access patterns
   - Maximizes potential feedback pool

### Additional Implementation Details

6. **Review Readiness**: Public status = ready for review (no additional flags)

7. **Discovery Features**: Dedicated `/drafts` table page with:
   - Recent activity sorting (default)
   - Comment count indicators
   - "New comments" badge for authors

### Additional Considerations

8. **Comment Moderation**: Should authors moderate comments on their drafts?
   - Use existing report system
   - Author can hide inappropriate comments
   - **Recommendation**: Stick with existing report system

9. **Metrics & Analytics**: What should we track?
   - Time in each state
   - Number of comments before submission
   - Review participation rates
   - **Recommendation**: Add basic metrics, expand based on usage

10. **Bulk Operations**: Support for multiple drafts?
    - Bulk status changes
    - Review dashboard for authors
    - **Recommendation**: Single draft operations only in Phase 1

## Implementation Phases

### Phase 1: Core Functionality (MVP)

- Add public state to draft model
- Implement "Make Public" action
- Enable commenting on public drafts
- Add public drafts to browse page
- Basic permission enforcement

### Phase 2: Discovery & Engagement

- Enhanced filtering and search
- Activity indicators
- Review metrics dashboard
- Email notifications (optional)

### Phase 3: Advanced Features

- Suggested reviewers
- Review templates
- Approval workflows
- Integration with external tools

## Success Metrics

- % of drafts going through public review
- Average number of comments per public draft
- Time from public to submitted
- Post-submission revision rate (should decrease)
- User satisfaction scores

## Risks & Mitigations

| Risk                      | Impact              | Mitigation                             |
| ------------------------- | ------------------- | -------------------------------------- |
| Low adoption              | Feature unused      | Incentivize reviews, showcase benefits |
| Spam/low-quality comments | Poor experience     | Leverage existing moderation tools     |
| Authors feel exposed      | Reluctance to share | Clear guidelines, supportive culture   |
| Performance degradation   | Slow page loads     | Implement caching, pagination early    |

## Dependencies

- Existing comment system (already implemented)
- Authentication system (already implemented)
- Redis for caching (already configured)

## Summary

This feature transforms the finding model creation process from a solo activity to a collaborative one, improving
quality through peer review while maintaining author control. The implementation leverages existing systems (comments,
auth, caching) and follows established UI patterns, making it a natural extension of the current platform.
