"""Test setup. Needs a Postgres database; set TEST_DATABASE_URL to point at one.

The environment is set before the app is imported, because settings are read
at import time.
"""
import os
import subprocess
import sys

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://tutor:tutor@localhost:5432/ai_tutor_test"
)
os.environ["DEMO_MODE"] = "true"
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

import httpx
import pytest_asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEMO_AUTH = {"Authorization": "Bearer access_token_user_123"}


@pytest_asyncio.fixture(scope="session")
async def client():
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True
    )
    from backend.main import app

    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            yield c
