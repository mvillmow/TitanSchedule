Run tests: $ARGUMENTS

If no arguments provided:

- Detect changed files from `git status` and `git diff --name-only`
- Identify which test files correspond to changed modules
- Run tests for those modules: `pixi run test`

If path provided:

- If it's a directory: `pixi run pytest $ARGUMENTS`
- If it's a file: `pixi run pytest $ARGUMENTS`

Show test results summary with pass/fail counts.
After tests complete, report any failures with file:line references.
