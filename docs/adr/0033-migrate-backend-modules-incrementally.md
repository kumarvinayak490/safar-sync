# Migrate Backend Modules Incrementally

TripOS will migrate backend code toward the domain-aligned module map incrementally.

The migration will reshape Django apps, Python packages, imports, behavior ownership, and eventually persisted model ownership around the target domain modules. Existing functionality must continue to work through compatibility imports while call sites move toward the new app and module names.

The first pass may add thin shims for old import paths. Those shims should be boring and temporary: they re-export the new module-owned behavior without becoming a second implementation.

Historical migrations should not be rewritten. Existing data must be preserved. Database table names should be preserved by default and renamed only when there is a specific value, with explicit safe migrations. Model ownership should move domain by domain so each step can be tested and handed off cleanly.

This favors reliability over a visually perfect one-shot refactor. The tradeoff is that old and new import paths may coexist briefly, but the backend can be moved safely without a flag-day database migration while still moving toward real domain Django apps.
