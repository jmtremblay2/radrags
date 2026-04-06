use UV for all runtime, builds, tests, etc.

use pytest for all tests (with UV)

every time you touch code, run `uv run black .`

## Documentation

The documentation strategy for this project is defined in `DOCUMENTATION.md`. Read it for all rules on docstring format, MkDocs configuration, and how to structure docs. Follow those rules whenever writing or updating code or documentation.

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

## Git Strategy

This project follows a **RED/GREEN TDD commit strategy** with **phase-level feature branches**.

### Branching

- `main` is the stable branch. It only receives merges at the end of a completed phase.
- For each phase, create a feature branch off `main` named `feat/phase-<N>-<short-description>` (e.g. `feat/phase-1-foundation`).
- Do **not** create sub-branches for individual steps. All step commits go directly on the phase branch.

### Commit Cadence

Each step within a phase produces exactly **two commits** on the feature branch:

1. **RED commit** — contains only the test(s) for that step. The test must be written and verified to fail before implementation begins.
2. **GREEN commit** — contains only the implementation that makes the test(s) pass. No refactoring, no unrelated changes.

### Commit Message Format
```
RED: <step description> - <what the test asserts>
GREEN: <step description> - <what was implemented>
```

Examples:
```
RED: Chunk dataclass - import and field assertions
GREEN: Chunk dataclass - add dataclass to chunker.py
RED: DocumentChunker ABC - TypeError on missing chunk()
GREEN: DocumentChunker ABC - add ABC with abstract method
```

### Merging

- Once all steps in a phase are complete (all tests passing), merge the feature branch into `main` using a **merge commit** (not squash, not rebase).
- This preserves the full RED/GREEN commit history inside `main`.

### Rules

- Never combine a RED and GREEN into a single commit.
- Never add implementation code in a RED commit.
- Never add new tests in a GREEN commit (only the implementation for the current RED).
- The RED commit must be reviewed and confirmed before the GREEN commit is written.