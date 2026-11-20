# Rise and Shine — Agent Instructions

## Git ownership
- Only the Owner performs Git operations.
- Agents must not run git status, diff, log, branch, add, commit, push or other Git commands.
- Report changed files without using Git.

## Testing
- Never create .pytest_tmp_* directories in the repository.
- By default, let pytest use the operating system's temporary directory.
- If --basetemp is required, use an absolute path outside the repository, derived from the operating system's temporary directory.
- Use separate temporary paths for concurrent test runs.
- Never delete test artifacts or audit evidence without Owner approval.

## Production safety
- Never deploy without explicit Owner authorization.
- Never recreate or reset the production PostgreSQL database.
- Before authorized deployment, require a fresh verified backup and preserve rollback capability.
- Do not invoke paid or live model APIs during tests.

## Development workflow
- Work only within the approved phase and scope.
- Codex implements and tests.
- Claude Code performs independent read-only audits.
- Owner reviews and accepts changes.
- Do not proceed to the next phase without Owner approval.
