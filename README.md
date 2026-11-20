# NextGen AI Tutor

An AI tutor for children aged 6–12, following England's National Curriculum. **Work in progress.**

- `PLAN.md` — what is being built, in what order, and why.
- `CODEBASE.md` — audit of the code this started from.
- `LEARNINGS.md` — working notes for whoever picks this up next.

## Where it stands

Phase 0 of the plan is done: the inherited demo has been cleaned up, its security holes closed, and it deploys. It is **not yet a tutor**. There are no real accounts (phase 1), the curriculum is placeholder data (phase 2), and the chat is the old prototype (replaced in phase 3).

Until phase 1, the page only works with `DEMO_MODE=true`, which lets one built-in demo child use it. Do not put real children's data in a demo-mode deployment.

## Run it locally

Needs Python 3.12 and Postgres.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # set DATABASE_URL; set DEMO_MODE=true to click around
alembic upgrade head          # creates the tables
uvicorn backend.main:app --port 5000
```

Open http://localhost:5000. Without `ANTHROPIC_API_KEY` the tutor says it is not connected.

## Tests

```bash
createdb ai_tutor_test
TEST_DATABASE_URL=postgresql+asyncpg://USER:PASS@localhost:5432/ai_tutor_test python -m pytest -q
```

`tests/test_security.py` has one test per hole found in the audit. CI runs the suite on every push (`.github/workflows/tests.yml`).

## Database changes

Tables are managed by Alembic, not created at startup.

```bash
alembic revision --autogenerate -m "what changed"   # after editing backend/core/database.py
alembic upgrade head
```

## Deploy (Railway)

The `Dockerfile` applies migrations and starts the server on Railway's `PORT`; `railway.json` sets the health check. The service needs these variables:

| Variable | Value |
|----------|-------|
| `DATABASE_URL` | Reference to the Railway Postgres service |
| `SECRET_KEY` | Long random string |
| `ENVIRONMENT` | `production` |
| `ANTHROPIC_API_KEY` | From console.anthropic.com |
| `DEMO_MODE` | `true` for a preview with no real data; otherwise unset |

All settings are listed in `.env.example`.

## Layout

```
backend/            FastAPI app
  main.py           entry point, static files
  core/             settings, database models
  api/v1/           routes
  claude_ai_service.py, multi_agent_tutor.py   prototype tutor (replaced in phase 3)
frontend/           the game-world page and parent dashboard
migrations/         Alembic
tests/
```
