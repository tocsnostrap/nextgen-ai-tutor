"""One test per hole found in the audit (CODEBASE.md section 4). Each probe must now fail."""
import uuid

from .conftest import bearer, make_parent


async def test_cannot_download_files_outside_frontend(client):
    for path in ("/frontend/..%2Fbackend%2Fcore%2Fconfig.py", "/frontend/..%2F.env.example"):
        r = await client.get(path)
        assert r.status_code == 404, path


async def test_frontend_files_still_served(client):
    r = await client.get("/frontend/icons.js")
    assert r.status_code == 200


async def test_made_up_tokens_rejected(client):
    for token in ("access_token_user_123", "access_token_anyone_i_like", "not-a-token"):
        r = await client.get("/api/v1/gamification/profile", headers=bearer(token))
        assert r.status_code == 401, token


async def test_no_token_rejected(client):
    r = await client.get("/api/v1/gamification/profile")
    assert r.status_code in (401, 403)


async def test_cannot_register_as_admin(client):
    tag = uuid.uuid4().hex[:10]
    r = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{tag}@example.com",
            "full_name": "Test Person",
            "password": "Passw0rd!xyz",
            "role": "admin",
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["role"] == "parent"


async def test_removed_user_routes_are_gone(client, family):
    for path in ("/api/v1/users/", f"/api/v1/users/{family['parent']['user_id']}", "/api/v1/analytics/overview"):
        r = await client.get(path, headers=family["a_auth"])
        assert r.status_code == 404, path


async def test_xp_award_is_capped(client, family):
    r = await client.post(
        "/api/v1/gamification/award-xp",
        headers=family["a_auth"],
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
