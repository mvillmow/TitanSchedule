Review PR #$ARGUMENTS comprehensively.

1. Get PR details: `gh pr view $ARGUMENTS`
2. Get the diff: `gh pr diff $ARGUMENTS`
3. Check CI status: `gh pr checks $ARGUMENTS`
4. Review the changes for:
   - Code correctness and logic
   - Python standards (type hints, docstrings, ruff compliance)
   - JavaScript standards (CDN-only, vanilla JS, no build tools, no frameworks)
   - Test coverage for new functionality
   - Documentation updates if needed
   - AES API patterns (negative IDs, proper header usage)
5. Provide structured feedback with specific file:line references
6. Summarize: approve, request changes, or comment
