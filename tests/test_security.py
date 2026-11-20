"""One test per hole found in the audit (CODEBASE.md section 4). Each probe must now fail."""
import uuid

from backend.core.config import settings

from .conftest import DEMO_AUTH


async def test_cannot_download_files_outside_frontend(client):
    for path in ("/frontend/..%2Fbackend%2Fcore%2Fconfig.py", "/frontend/..%2F.env.example"):
        r = await client.get(path)
        assert r.status_code == 404, path


async def test_frontend_files_still_served(client):
    r = await client.get("/frontend/icons.js")
    assert r.status_code == 200


async def test_made_up_token_rejected(client):
    r = await client.get(
        "/api/v1/gamification/profile",
        headers={"Authorization": "Bearer access_token_anyone_i_like"},
    )
    assert r.status_code == 401


async def test_no_token_rejected(client):
    r = await client.get("/api/v1/gamification/profile")
    assert r.status_code in (401, 403)


async def test_demo_token_only_works_in_demo_mode(client, monkeypatch):
    r = await client.get("/api/v1/gamification/profile", headers=DEMO_AUTH)
    assert r.status_code == 200
    monkeypatch.setattr(settings, "DEMO_MODE", False)
    r = await client.get("/api/v1/gamification/profile", headers=DEMO_AUTH)
    assert r.status_code == 401


async def test_cannot_register_as_admin(client):
    tag = uuid.uuid4().hex[:10]
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{tag}@example.com",
            "username": f"user{tag}",
            "full_name": "Test Person",
            "password": "Passw0rd!xyz",
            "role": "admin",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "student"


async def test_cannot_read_another_child(client):
    r = await client.get("/api/v1/parent/weekly-report/someone_else", headers=DEMO_AUTH)
    assert r.status_code == 403
    r = await client.get("/api/v1/parent/weekly-report/user_123", headers=DEMO_AUTH)
    assert r.status_code == 200


async def test_xp_award_is_capped(client):
    r = await client.post(
        "/api/v1/gamification/award-xp",
        headers=DEMO_AUTH,
        json={"amount": 999999, "reason": "test"},
    )
    assert r.status_code == 200
    assert r.json()["xp_awarded"] == 100


async def test_api_docs_not_public(client):
    for path in ("/docs", "/redoc", "/openapi.json"):
        r = await client.get(path)
        assert r.status_code == 404, path


async def test_no_cross_origin_access_by_default(client):
    r = await client.get("/health", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in r.headers
