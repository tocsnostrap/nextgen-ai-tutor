"""Test setup. Needs a Postgres database; set TEST_DATABASE_URL to point at one.

The environment is set before the app is imported, because settings are read
at import time.
"""
import os
import subprocess
import sys
import uuid

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+asyncpg://tutor:tutor@localhost:5432/ai_tutor_test"
)
os.environ["DEBUG"] = "false"
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("ANTHROPIC_API_KEY", None)
os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

import httpx
import pytest_asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PASSWORD = "Passw0rd!xyz"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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


async def make_parent(client) -> dict:
    """Register a new parent; returns the token response plus the email used."""
    email = f"{uuid.uuid4().hex[:12]}@example.com"
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "full_name": "Test Parent", "password": PASSWORD},
    )
    assert r.status_code == 201, r.text
    return {**r.json(), "email": email}


async def make_child(client, parent_token: str, name: str = "Sam", year: int = 3, pin: str = "1234") -> dict:
    r = await client.post(
        "/api/v1/family/children",
        headers=bearer(parent_token),
        json={"display_name": name, "school_year": year, "pin": pin},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def child_token(client, parent_token: str, child_id: str, pin: str = "1234") -> str:
    r = await client.post(
        f"/api/v1/family/children/{child_id}/session",
        headers=bearer(parent_token),
        json={"pin": pin},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest_asyncio.fixture(scope="session")
async def family(client):
    """One parent with two children, and a signed-in session for each."""
    parent = await make_parent(client)
    a = await make_child(client, parent["access_token"], "Amira", 3)
    b = await make_child(client, parent["access_token"], "Zayd", 6)
    return {
        "parent": parent,
        "a": a,
        "b": b,
        "a_auth": bearer(await child_token(client, parent["access_token"], a["id"])),
        "b_auth": bearer(await child_token(client, parent["access_token"], b["id"])),
        "parent_auth": bearer(parent["access_token"]),
    }
