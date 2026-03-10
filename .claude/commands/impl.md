Implement GitHub issue #$ARGUMENTS.

1. Read issue context: `gh issue view $ARGUMENTS --comments`
2. Understand requirements and acceptance criteria
3. Create feature branch: `git checkout -b $ARGUMENTS-<desc>`
4. Implement the changes following project standards from CLAUDE.md
5. Run tests to verify: `pixi run test`
6. Commit with conventional commit format
7. Create PR linked to issue: `gh pr create --body "Closes #$ARGUMENTS"`
