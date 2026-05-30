# TripOS

TripOS is an operations-first platform for paid group trips. This repository uses a lightweight monorepo with Django DRF, Next.js, a worker runtime, and local infrastructure for Postgres, Redis, and S3-compatible object storage.

## Quick Start

Requirements:

- `uv`
- `pnpm`
- `docker`
- `just`

```sh
just install
just dev
```

Then open:

- API health: http://localhost:8000/api/health/
- Web app: http://localhost:3000
- MinIO console: http://localhost:9001

More setup details are in [docs/development/local-development.md](docs/development/local-development.md).

## Root Commands

- `just dev` starts local infrastructure, the API, and the web app.
- `just services` starts Postgres, Redis, and MinIO.
- `just api` starts Django.
- `just web` starts Next.js.
- `just worker` runs the worker once.
- `just test` runs backend and frontend smoke tests.
- `just lint` runs backend and frontend lint checks.
- `just format` formats backend and frontend code.
- `just build` runs frontend and backend build checks.
- `just migrate` applies Django migrations.
- `just smoke` runs the scripted CI-style smoke path.
