# Domain Docs

This repo uses a multi-context domain layout.

## Before exploring, read these

- `CONTEXT-MAP.md` at the repo root
- `docs/contexts/shared/CONTEXT.md`
- The focused `docs/contexts/**/CONTEXT.md` files relevant to the area being changed
- `docs/adr/` for architectural decisions that touch the area being changed

The root `CONTEXT.md` remains as the full historical context while focused contexts stabilize. Prefer `CONTEXT-MAP.md` and the focused context files for new work. Use root `CONTEXT.md` only when a term has not yet been copied into a focused context.

## Context Selection

Use `CONTEXT-MAP.md` to choose the smallest useful context packet.

- Organizer root work: read `docs/contexts/organizers/CONTEXT.md`
- Organizer public content: read `organizer_profile`, `organizer_media`, and `organizer_policies`
- Organizer access: read `team_access`
- Organizer payment setup: read `organizer_payments`
- Creative generation preferences: read `creative_setup`
- Trip profile and public trip page work: read `trips`
- Booking lifecycle work: read `trip_bookings`
- Traveler readiness work: read `trip_travelers`
- Booking payment and ledger work: read `trip_payments`
- Communications, exports, and activity work: read `trip_operations`
- Demand pages and SEO discovery work: read `public_discovery`
- Staff orchestration work: read `internal_admin`

## Use The Glossary's Vocabulary

When output names a domain concept, use the term as defined in the most specific context file. Do not drift to synonyms the glossary explicitly avoids.

If the concept needed is missing from the focused context, check root `CONTEXT.md`. If it exists there, copy or summarize it into the focused context before using it heavily. If it does not exist, avoid inventing language or note the gap for `grill-with-docs`.

## Flag ADR Conflicts

If output contradicts an existing ADR, surface it explicitly rather than silently overriding it.
