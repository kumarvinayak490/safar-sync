#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== Backend lint =="
uv run --project apps/api ruff check apps/api apps/worker

echo "== Backend tests =="
uv run --project apps/api pytest apps/api

echo "== Migration check =="
uv run --project apps/api python apps/api/manage.py makemigrations --check --dry-run

echo "== Frontend lint =="
pnpm --dir apps/web lint

echo "== Frontend tests =="
pnpm --dir apps/web test

echo "== Frontend build =="
pnpm --dir apps/web build
