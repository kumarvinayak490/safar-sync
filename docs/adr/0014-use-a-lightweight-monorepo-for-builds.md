# Use a Lightweight Monorepo for Builds

TripOS will use a single monorepo for the MVP, with separate app folders for the Django API, Next.js web app, background worker/runtime code, and deployment/infrastructure configuration. This keeps product decisions, domain docs, API contracts, migrations, frontend changes, worker behavior, and CI in one place while the product is still tightly coupled and moving quickly.

The monorepo should stay lightweight rather than adopting a heavy monorepo platform. Use language-native tooling inside each app and a small root command runner to compose common workflows:

- `apps/api` — Django + DRF backend, managed with `uv`, tested with `pytest`, linted/formatted with `ruff`
- `apps/web` — Next.js frontend, managed with `pnpm`, checked with TypeScript, ESLint, and the framework build
- `apps/worker` or API-managed worker module — background jobs for reminders, payment processing, exports, and file processing
- `packages/api-client` — generated TypeScript API client only once the API contract stabilizes enough to justify it
- `infra` — Docker Compose for local dependencies and deployment configuration
- root `justfile` — one command surface for `dev`, `test`, `lint`, `format`, `build`, `migrate`, and `worker`

Local development should run Postgres, Redis, and local object storage through Docker Compose, while the API, worker, and web app can run directly on the host for faster iteration. CI should run backend lint/tests, frontend typecheck/lint/build, migration checks, and a small set of contract or smoke tests. Production builds should package the Django API and worker as containers, while the Next.js app can be deployed separately as the public/traveler/operations web surface.

The main rejected alternative is a polyrepo split between frontend, backend, and infrastructure. That would add coordination overhead before the team has enough independent deployment boundaries to justify it. Heavy tools such as Nx or Turborepo may be useful later if shared packages, caching, and many frontend apps become painful, but they are unnecessary for the first MVP.
