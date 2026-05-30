# Issue tracker: Local Markdown

Issues and PRDs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The PRD is `.scratch/<feature-slug>/PRD.md`
- Implementation issues are `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01`
- Triage state is recorded as a `Status:` line near the top of each issue file
- Comments and conversation history append to the bottom of the file under a `## Comments` heading

## Status lifecycle

Use these `Status:` values for implementation work:

- `ready-for-agent` means fully specified and eligible once dependencies are done
- `in-progress` means assigned to an active worker
- `blocked` means work stopped on a concrete blocker documented under `## Comments`
- `ready-for-review` means implementation is complete but awaiting orchestrator verification
- `done` means the orchestrator accepted the work and verification passed

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/`, creating the directory if needed.

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.
