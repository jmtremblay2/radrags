use UV for all runtime, builds, tests, etc.

use pytest for all tests (with UV)

every time you touch code, run `uv run black .`

When writing package code, follow Red/Green testing:
1. Write a failing test first (`uv run pytest` must fail with the expected assertion).
2. Write the minimal production code to make the test pass.
3. Run `uv run pytest` to confirm green.
Do not skip step 1 — the test must be seen failing before writing the implementation.

## Workflow for every task

Follow these three phases in order. Do not jump ahead.

1. **DEFINE** — Clarify the goal. The user maintains `DESCRIBE.md` as the source of truth for what the project/task is about. Read it first. Restate what the user wants to achieve and confirm understanding before proceeding. Ask questions if anything is ambiguous.
2. **PLAN** — Break the work into small, concrete, verifiable steps. Present the plan to the user for approval. Each step should be small enough that its result can be independently checked.
3. **EXECUTE** — Carry out each step one at a time. After each step, show the user what changed and how to verify it (e.g. test output, diff, command result). Wait for confirmation before moving to the next step if the outcome is unclear.