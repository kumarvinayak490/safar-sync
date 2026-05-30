set dotenv-load := false

api_dir := "apps/api"
web_dir := "apps/web"

install:
    uv sync --project {{api_dir}}
    pnpm --dir {{web_dir}} install

services:
    docker compose -f infra/docker-compose.yml up -d

dev: services
    just --parallel api web

api:
    uv run --project {{api_dir}} python {{api_dir}}/manage.py runserver 0.0.0.0:8000

web:
    pnpm --dir {{web_dir}} dev

worker:
    uv run --project {{api_dir}} python apps/worker/worker.py --once

migrate:
    uv run --project {{api_dir}} python {{api_dir}}/manage.py migrate

test:
    uv run --project {{api_dir}} pytest {{api_dir}}
    pnpm --dir {{web_dir}} test

lint:
    uv run --project {{api_dir}} ruff check {{api_dir}} apps/worker
    pnpm --dir {{web_dir}} lint

format:
    uv run --project {{api_dir}} ruff format {{api_dir}} apps/worker
    pnpm --dir {{web_dir}} format

build:
    uv run --project {{api_dir}} python {{api_dir}}/manage.py check
    pnpm --dir {{web_dir}} build

smoke:
    scripts/smoke.sh
