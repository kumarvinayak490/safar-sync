# Ralph Loop: Domain Backend App Split

This file is the feature-specific orchestration plan for `.scratch/domain-backend-app-split/`.

The main orchestrator owns issue selection, worker spawning, integration, verification, and issue status updates. Each worker gets exactly one issue in a fresh session with an explicit context packet.

## Operating Model

- TripOS remains one Django project, one backend process, one deployment unit, and one database.
- Workers may proceed autonomously for normal implementation work inside the active runtime permissions.
- If the runtime blocks a required command, the worker or orchestrator should request the permission once and use a reusable prefix rule when appropriate.
- Workers must not run destructive commands such as `git reset --hard`, broad deletes, history rewrites, or unrelated cleanup.
- The orchestrator, not workers, marks issues `done` after integration and verification.

## Issue Eligibility

An issue is eligible when:

- `Status:` is `ready-for-agent`.
- Every file listed under `## Blocked by` is `done`.
- No active worker owns the same code area.
- The issue does not require a decision that contradicts the PRD, focused contexts, or ADRs.

When assigning an issue:

- Change `Status: ready-for-agent` to `Status: in-progress`.
- Add a `## Comments` entry with timestamp, worker name/id, and ownership notes.

When accepting worker output:

- Inspect changed files for scope.
- Run the issue-level checks and any broader checks required by touched shared contracts.
- Change `Status:` to `done` only after verification.
- Add a completion comment with summary, checks, and risks.

## Default Worker Context Packet

Every worker should read:

- `AGENTS.md`
- `CONTEXT-MAP.md`
- `CONTEXT.md`
- `docs/agents/domain.md`
- `docs/agents/issue-tracker.md`
- `docs/agents/ralph-loop.md`
- `.scratch/domain-backend-app-split/PRD.md`
- The assigned issue file
- Relevant completed dependency issues
- Relevant focused contexts from `docs/contexts/`
- Relevant ADRs from `docs/adr/`

Always include these ADRs for backend split work:

- `docs/adr/0013-use-django-drf-and-nextjs-for-the-mvp.md`
- `docs/adr/0014-use-a-lightweight-monorepo-for-builds.md`
- `docs/adr/0032-use-domain-aligned-backend-module-map.md`
- `docs/adr/0033-migrate-backend-modules-incrementally.md`
- `docs/adr/0035-split-backend-into-domain-django-apps.md`

Include `docs/adr/0034-use-python-domain-packages-before-django-app-splits.md` as superseded background when a worker may encounter older guidance.

## Current Loop

All issues in this migration wave are complete.

Active workers:

- None

Use this as the reference template for the next domain split wave:
update the "Current Loop" and "Parallelism Plan" sections to the next scope.

## Parallelism Plan

Use max concurrency `2` by default. Raise only when write scopes are clearly disjoint and the orchestrator can still verify results carefully.

Safe waves once blockers are done:

- After `01`: `02` and `35` may run together if `35` only touches Internal Admin shell code.
- After `02`: `03` should run alone because it defines Organizer root cleanup.
- After `03`: `04`, `09`, `11`, and `14` are independent domain moves. Run at most two at a time.
- After `04`: `06`, `07`, and `08` are mostly independent. Run at most two at a time.
- After `06`: `05` can add Organizer Profile publication rules using Organizer Policies readiness.
- After `11`: `12` and `13` may run together if their write scopes stay inside Organizer Payments.
- After `14`: `15` then `16` should run in sequence because Public Trip Page readiness depends on trip content ownership.
- After `11` and `16`: `17` should run before booking lifecycle work.
- After `18`: `19`, `20`, and `21` can be parallelized carefully if access-link and traveler-slot changes do not touch the same models/migrations.
- After `21`: `22` can run.
- After `18` and `21`: `23` can run.
- After `23`: `24` and `26` can run if provider payment and manual review scopes stay separate.
- After `24`: `25` and `27` can run if capacity/payment exception scopes stay separate.
- After `28`: `29` and `30` can run together.
- Public Discovery should run as `31`, `32`, then `33` and `34`.
- Internal Admin can start with `35`, then `36` after `32`, and `37` after `27`.
- `38`, `39`, and `40` are final integration issues and should run one at a time.

## Worker Prompt

Use this template:

```md
You are a fresh worker agent on the TripOS repo at /Users/vin/Documents/safar-sync.

You are not alone in the codebase. Other agents may be working in parallel, so keep edits scoped and do not revert unrelated changes.

Assigned issue:
<issue path>

Context to read first:
- AGENTS.md
- CONTEXT-MAP.md
- CONTEXT.md
- docs/agents/domain.md
- docs/agents/issue-tracker.md
- docs/agents/ralph-loop.md
- .scratch/domain-backend-app-split/RALPH-LOOP.md
- .scratch/domain-backend-app-split/PRD.md
- <assigned issue path>
- <relevant dependency issue paths>
- <relevant focused context paths>
- <relevant ADR paths>

Autonomy:
Proceed without human approval for normal implementation actions inside active runtime permissions. If a required command is blocked by the sandbox, request the needed permission once with a reusable prefix rule when appropriate. Do not run destructive commands, history rewrites, broad deletes, or unrelated cleanup.

Task:
Implement only the assigned issue end to end. Add or update tests, run relevant checks, and update the issue with a short completion comment. Do not mark the issue done; the orchestrator verifies and marks done.

Return:
- Summary
- Files changed
- Checks run
- Known risks or follow-up needed
```
