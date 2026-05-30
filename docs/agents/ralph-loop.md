# Ralph Loop Orchestration

Ralph Loop is the autonomous implementation workflow for this repo.

One main orchestrator repeatedly reads the local issue tracker, chooses unblocked work, launches fresh worker agents, integrates their results, verifies the repo, updates issue status, and loops.

## RALPH cycle

1. Read the issue graph.
2. Assign one unblocked issue to each worker.
3. Launch fresh worker sessions with context packets.
4. Probe worker results and integrate changes.
5. Harvest verification output, update issue state, and loop.

## Roles

### Orchestrator

The orchestrator is the only agent responsible for:

- Selecting issues from `.scratch/<feature-slug>/issues/`
- Deciding whether issues can run in parallel
- Preparing the context packet for each worker
- Spawning fresh worker sessions
- Reviewing and integrating worker changes
- Running final verification after integration
- Updating issue status and comments
- Resolving merge conflicts or overlapping work
- Deciding the next loop iteration
- Enforcing the frontend quality bar for every web-facing issue

### Worker

A worker is responsible for exactly one issue.

A worker should:

- Treat the assigned issue as the source of truth for scope
- Read the provided context packet before editing
- Implement the issue end to end
- Add or update tests appropriate to the issue risk
- Run the most relevant checks available in the repo
- Keep edits scoped to the issue
- Avoid reverting unrelated work
- Return a concise handoff with changed files, checks run, and known risks

A worker should not pick additional issues, widen scope, or wait for human product decisions unless the issue contradicts the PRD, `CONTEXT.md`, or an ADR.

## Frontend quality bar

Every worker that touches the web app must use both the `frontend-design` and `impeccable` skills.

Read `PRODUCT.md` and `DESIGN.md` before making frontend edits. `PRODUCT.md` defines the product register, users, purpose, brand personality, anti-references, design principles, and accessibility goals. `DESIGN.md` defines the starter visual system.

TripOS should feel like a refined operations product for repeat community-led trip organizers running paid trips. The UI should be calm, trustworthy, dense enough for real work, and visually specific to payments, traveler readiness, and group-trip operations.

Frontend work should avoid:

- Generic SaaS landing-page composition
- Purple-gradient startup aesthetics
- Decorative travel imagery that does not help operations
- Oversized marketing heroes inside dashboard/product surfaces
- Cards nested inside cards
- UI copy that explains how the interface works instead of making controls clear

Frontend work should prefer:

- Strong information hierarchy for organizers managing 10-80 travelers
- Crisp tables, queues, status chips, ledgers, and operational controls
- Business-appropriate color systems with sparing accents
- Clear empty, loading, error, and permission states
- Mobile-safe public booking and traveler portal flows
- Accessible controls and predictable keyboard/focus behavior

If the `frontend-design` skill and this repo guide disagree, follow the repo guide for product fit and use the skill for execution quality.

## Permission model

The intended mode is autonomous execution. Workers should proceed without human approval for normal implementation actions, including creating files, editing code, running tests, running formatters, adding migrations, installing declared dependencies, and starting local services.

Permission is still bounded by the active Codex/runtime sandbox. If a command is blocked by the runtime, the orchestrator should request the needed permission once, with a reusable prefix rule when appropriate.

Workers must not run destructive commands such as `git reset --hard`, broad deletes, or history rewrites unless the assigned issue explicitly requires it and the orchestrator has isolated the work in a disposable branch or worktree.

## Issue selection

An issue is eligible when:

- `Status:` is `ready-for-agent`
- Every issue listed under `## Blocked by` is `done`
- The issue is not already assigned in the current loop

Pick the lowest-numbered eligible issues first unless a later issue is clearly safer to run in parallel and does not block earlier core flows.

When an issue is assigned, change:

```md
Status: ready-for-agent
```

to:

```md
Status: in-progress
```

Append a short `## Comments` entry with the worker assignment and start time.

## Parallelism

Default max concurrency is 2 workers.

Spawn two workers only when both conditions are true:

- Both issues are unblocked by completed dependencies
- The issues have low overlap in expected write areas

Do not parallelize issues that both need to change the same core model, migration sequence, API contract, or shared workflow unless one worker is explicitly scoped to tests/docs and the other to implementation.

If only one issue is eligible, spawn one worker.

## Fresh worker context packet

Each worker must start from a fresh session. Do not rely on hidden orchestrator memory.

Provide this context explicitly:

- `AGENTS.md`
- `PRODUCT.md`
- `DESIGN.md`
- `CONTEXT.md`
- `docs/agents/domain.md`
- `docs/agents/issue-tracker.md`
- The assigned issue file
- The parent PRD listed in the issue
- Relevant ADRs from `docs/adr/`
- Completed dependency issue summaries
- Current repository status and any known in-progress worker ownership

For early TripOS issues, always include:

- `docs/adr/0013-use-django-drf-and-nextjs-for-the-mvp.md`
- `docs/adr/0014-use-a-lightweight-monorepo-for-builds.md`

Add more ADRs based on the domain area being touched.

## Worker prompt template

Use this structure when launching a worker:

```md
You are a fresh worker agent on the TripOS repo.

You are not alone in the codebase. Other agents may be working in parallel, so keep your edits scoped and do not revert unrelated changes.

Assigned issue:
<path>

Context to read first:
- AGENTS.md
- CONTEXT.md
- docs/agents/domain.md
- docs/agents/issue-tracker.md
- docs/agents/ralph-loop.md
- <parent PRD path>
- <relevant ADR paths>
- <completed dependency issue paths or summaries>

Your task:
Implement only the assigned issue end to end. If you touch the web app, use the frontend-design and impeccable skills, read PRODUCT.md and DESIGN.md, and meet the frontend quality bar in docs/agents/ralph-loop.md. Add or update tests, run relevant checks, and update the issue with a short completion comment.

Return:
- Summary
- Files changed
- Checks run
- Known risks or follow-up needed
```

## Integration and verification

When a worker completes, the orchestrator should:

- Inspect the worker's changed files
- Check for unrelated edits
- Run the relevant test/build/lint commands
- Run broader smoke checks when shared contracts changed
- Resolve conflicts if another worker also changed nearby code
- Update dependent issue readiness only after successful verification

When accepted, change the issue status to:

```md
Status: done
```

Append a `## Comments` entry with:

- Completion summary
- Verification commands
- Any follow-up issue references

If the worker cannot finish because of a real blocker, change status to:

```md
Status: blocked
```

and document the blocker under `## Comments`.

## Current TripOS issue graph

At the initial state, only issue `01` is unblocked.

The first loop should spawn one worker for:

- `.scratch/tripos-mvp/issues/01-scaffold-lightweight-monorepo-and-ci-smoke-path.md`

Early safe parallel opportunities appear later:

- After issue `06`, issues `07` and `10` may be parallelized if API boundaries are clear.
- After issue `08`, issues `09` and `14` may be parallelized if dashboard work and manual booking work are scoped separately.
- After issue `13`, issues `19` and `20` may be parallelized if background reminder scheduling and manual announcements use separate modules.

The orchestrator should recompute eligibility from issue files every loop instead of trusting this static note.
