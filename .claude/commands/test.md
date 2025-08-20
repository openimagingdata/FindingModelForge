Generate comprehensive unit tests for $ARGUMENTS following these rules:

1. Use our existing test framework patterns (see `tests/CLAUDE.md`)
2. Include edge cases and error scenarios
3. Aim for 80%+ coverage
4. Group related tests in describe blocks
5. Use clear test descriptions that explain the expected behavior
6. Include both positive and negative test cases
7. Test async operations properly
8. Clean up any test data/mocks after each test
9. Test ONLY our application logic--do NOT test underlying services.

IMPORTANT: FIRST: Analyze the existing test patterns in this codebase. Identify the testing framework and assertion
style we're using. THEN: Plan what test cases are needed for comprehensive coverage. FINALLY: Then write the actual test
code following our patterns
