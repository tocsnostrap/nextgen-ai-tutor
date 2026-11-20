# NextGen AI Tutor

An AI tutor for children aged 6–12, following England's National Curriculum. **Work in progress.**

- `PLAN.md` — what is being built, in what order, and why.
- `CODEBASE.md` — audit of the code this started from.
- `LEARNINGS.md` — working notes for whoever picks this up next.

## Where it stands

Phases 0 and 1 of the plan are done: the inherited demo has been cleaned up, its security holes closed, it deploys, and it has real accounts. It is **not yet a tutor**: the curriculum is placeholder data (phase 2) and the chat is the old prototype (replaced in phase 3).

## Accounts

A parent creates an account at `/account` and adds each child (name, school year, picture, 4-digit PIN). The device stays signed in; a child taps their picture and enters their PIN. Each child's record is separate and saved in Postgres. Adding children and opening the parent dashboard (`/parent`) ask for the parent's password.

## Run it locally

Needs Python 3.12 and Postgres.

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env          # set DATABASE_URL
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

All settings are listed in `.env.example`.

## Layout

```
backend/            FastAPI app
  main.py           entry point, static files
  core/             settings, database models
  api/v1/           routes
  claude_ai_service.py, multi_agent_tutor.py   prototype tutor (replaced in phase 3)
frontend/           account.html (sign in, who's learning), index.html (game world), parent dashboard
migrations/         Alembic
tests/
```
