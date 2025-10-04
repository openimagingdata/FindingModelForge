---
description: Implement a development plan step-by-step with careful review at each stage
mode: agent
---

# Implement Development Plan

You are tasked with implementing a development plan systematically and thoughtfully. This prompt guides you through executing a multi-phase plan while maintaining high code quality and alignment with project standards.

## Reference the Plan

The plan you're implementing: [${input:planFile:Path to plan file (e.g., tasks/my-plan.md)}]

Also reference our coding standards (paths are relative to the workspace root):

- Project guidelines: `CLAUDE.md`
- Backend standards: `app/CLAUDE.md`
- Frontend standards: `templates/CLAUDE.md`
- Testing standards: `tests/CLAUDE.md`
- UI Testing standards: `tests/ui/README.md`

## Implementation Approach

You will work through the plan **one phase at a time**. For each phase:

### Before Starting Implementation

1. **Understand the Phase**
   - Read the phase description and all checklist items carefully
   - Identify what this phase accomplishes
   - Understand how it fits into the larger plan (what comes before/after)
   - Note any dependencies on previous phases

2. **Clarify the End Goal**
   - What specific deliverables should exist when this phase is complete?
   - What should be testable/verifiable?
   - What success criteria apply to this phase?

3. **Think Through the Implementation**
   - Consider multiple approaches to accomplish the goals
   - Identify potential pitfalls or edge cases
   - Think about how to keep the implementation simple (YAGNI principle)
   - Plan how to maintain alignment with our coding standards:
     * Type safety (extensive type hints)
     * Async patterns (async/await for I/O)
     * UI components (Flowbite + Alpine.js only)
     * Test coverage (100% pass rate maintained)
     * Code organization (follow existing patterns)
   - Consider how changes will be tested

4. **Confirm Readiness**
   - Do you have all the context needed from previous phases?
   - Are there any blockers or unknowns to resolve first?
   - Is the approach aligned with the plan AND our standards?

### During Implementation

- **Follow the plan** but adapt intelligently if you discover better approaches
- **Use existing patterns** from the codebase rather than inventing new ones
- **Keep it simple** - don't over-engineer or add unnecessary complexity
- **Write code incrementally** - test as you go rather than big-bang changes
- **Maintain type safety** - comprehensive type hints throughout
- **Follow async patterns** - async/await for all I/O operations
- **Respect UI rules** - Flowbite components + Alpine.js for frontend (never custom CSS/JS)

### After Completing the Phase

**CRITICAL: STEP BACK AND ASSESS**

Before moving to the next phase, thoroughly evaluate what you've implemented:

1. **Completion Check**
   - Have ALL checklist items for this phase been completed?
   - Are there any partial implementations or TODOs left behind?
   - Is the code in a fully functional, testable state?

2. **Code Quality Review**
   - Does the code follow our project standards? (Check CLAUDE.md files)
   - Are type hints comprehensive and accurate?
   - Are async patterns used correctly?
   - For UI: Are we using ONLY Flowbite components + Alpine.js?
   - Is error handling appropriate?
   - Are edge cases handled?

3. **Simplicity Assessment**
   - Have we over-engineered anything?
   - Could any code be simpler or more straightforward?
   - Is there duplication that can be eliminated?
   - Are we following YAGNI (You Aren't Gonna Need It)?
   - Have we introduced unnecessary abstractions?

4. **Testing & Verification**
   - Does the code have appropriate test coverage?
   - Do all existing tests still pass?
   - Are new tests needed for new functionality?
   - Can the changes be verified manually if needed?

5. **Integration Check**
   - Do the changes integrate cleanly with existing code?
   - Are there any breaking changes or compatibility issues?
   - Does this phase properly enable the next phase?

6. **Documentation**
   - Are code comments clear and helpful?
   - Do docstrings accurately describe behavior?
   - Are any README or documentation updates needed?

### Decision Point

After assessment, decide:
- ✅ **Phase complete**: All criteria met, ready to move to next phase
- ⚠️ **Needs refinement**: Identified issues that should be fixed before proceeding
- ❌ **Reconsider approach**: Fundamental issues requiring a different implementation strategy

**DO NOT** proceed to the next phase until the current phase assessment shows green checkmarks across all criteria.

## Iteration Process

1. Start with Phase 1
2. Complete pre-implementation thinking
3. Implement the phase
4. Perform post-implementation assessment
5. Refine if needed
6. Only when phase is truly complete, move to Phase 2
7. Repeat until all phases complete

## Final Deliverable Check

After completing ALL phases, perform a final holistic review:

- ✅ All phases completed successfully
- ✅ All success criteria from the plan met
- ✅ Code follows project standards throughout
- ✅ Tests at 100% pass rate
- ✅ No over-engineering or unnecessary complexity
- ✅ Documentation updated where needed
- ✅ Changes are ready for review/merge

## Key Principles

- **One phase at a time** - Don't skip ahead or try to do multiple phases simultaneously
- **Think before coding** - Planning prevents mistakes
- **Assess after implementing** - Catch issues early
- **Follow existing patterns** - Consistency matters
- **Keep it simple** - Complexity is the enemy
- **Maintain quality** - Never sacrifice standards for speed

## Remember

The goal is not just to complete the plan, but to complete it **well** - with clean, maintainable, well-tested code that aligns with our project's high standards. Take your time at each phase to get it right.
