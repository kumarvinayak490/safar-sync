# AGENTS.md

## Agent skills

### Issue tracker

Issues and PRDs are tracked as local markdown files under `.scratch/`. See `docs/agents/issue-tracker.md`.

### Triage labels

The repo uses the default triage label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a multi-context repo with root `CONTEXT-MAP.md`, focused contexts under `docs/contexts/`, and ADRs under `docs/adr/`. See `docs/agents/domain.md`.

### Ralph Loop orchestration

For autonomous implementation runs, use `docs/agents/ralph-loop.md`.

The orchestrator owns issue selection, context packets, worker spawning, integration, verification, and issue status updates. Each worker gets one issue in a fresh session with only the relevant docs and dependency context needed for that task.

### Design context

Frontend work must use both `frontend-design` and `impeccable`.

Design strategy lives in `PRODUCT.md`; visual system guidance lives in `DESIGN.md`. Treat TripOS as a product UI for paid group-trip operations: calm, exacting, field-ready, and focused on payment/reconciliation/readiness workflows.
