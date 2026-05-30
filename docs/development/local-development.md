# Local Development

TripOS uses a lightweight monorepo:

- `apps/api` contains the Django DRF API.
- `apps/web` contains the Next.js web app.
- `apps/worker` contains the worker runtime entrypoint.
- `infra` contains local dependency services.
- `scripts` contains composed smoke checks.

## Environment

Copy `apps/api/.env.example` to `apps/api/.env` if you want to override defaults. The local defaults target Docker Compose services:

- Postgres: `postgres://tripos:tripos@localhost:5432/tripos`
- Redis: `redis://localhost:6379/0`
- Object storage endpoint: `http://localhost:9000`

The web app reads `NEXT_PUBLIC_API_BASE_URL` and defaults to `http://localhost:8000`.

Local file uploads default to `apps/api/.local/media`, which is intentionally ignored by Git.
Set `DJANGO_MEDIA_ROOT` when you need a different local upload directory.

## Commands

Install dependencies:

```sh
just install
```

Start Postgres, Redis, MinIO, the API, and the web app:

```sh
just dev
```

Run migrations:

```sh
just migrate
```

Run the worker once:

```sh
just worker
```

Run the CI-style smoke path:

```sh
just smoke
```

## Health Checks

- API: `GET /api/health/`
- Web: the Operations Dashboard start screen displays API health state.

The scaffold intentionally keeps domain models out of the first issue. Later issues should add Organizer, Trip, Booking, Traveler, payment, and readiness models behind migrations and focused tests.
