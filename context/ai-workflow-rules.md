# AI Workflow Rules

## Approach

Build this project incrementally using a spec-driven workflow. Context files define what to build (`project-overview.md`), how it is structured (`architecture.md`), and the current state of progress (`progress-tracker.md`). Always implement against these specs. Do not infer or invent behavior from scratch.

At the start of every session: read `progress-tracker.md`, identify the first unit under **Next Up**, and implement only that unit unless told otherwise.

## Scoping Rules

- Work on one unit at a time as defined in `progress-tracker.md`.
- Prefer small, verifiable increments over large speculative changes.
- Do not combine unrelated system boundaries in a single implementation step.
- Each unit has a defined **Verify** step. Do not move to the next unit until that step passes.

## When to Split Work

Split an implementation step if:

- Behavior not clearly defined in `project-overview.md` or `architecture.md`.

If a change cannot be verified end to end quickly, the scope is too broad — split it.

## Handling Missing Requirements

- If a requirement is ambiguous, resolve it in the relevant context file before implementing.
- If a requirement is missing, add it as an open question in `progress-tracker.md` before continuing.

## Keeping Docs in Sync

Update the relevant context file whenever implementation changes affect:

- Module boundaries or the file plan (`architecture.md`).
- localStorage key names or data shapes (`architecture.md` and `progress-tracker.md` Architecture Decisions).
- Feature scope or success criteria (`project-overview.md`).
- Completed / in-progress / next-up status (`progress-tracker.md`).

## Before Moving to the Next Unit

1. The unit's **Verify** step passes end to end.
2. No invariant defined in `architecture.md` was violated.
3. `progress-tracker.md` has been updated: the unit moved from **Next Up** → **Completed**, and the next unit is now listed as **Current Goal**.
