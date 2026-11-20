"""Parent accounts, child profiles, PIN sessions, and separate saved records."""
from .conftest import PASSWORD, bearer, child_token, make_child, make_parent


async def test_login_and_refresh(client):
    parent = await make_parent(client)
    r = await client.post("/api/v1/auth/login", json={"email": parent["email"], "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["role"] == "parent"

    r = await client.post("/api/v1/auth/login", json={"email": parent["email"], "password": "wrong-password"})
    assert r.status_code == 401

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": parent["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]

    # An access token is not accepted as a refresh token.
    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": parent["access_token"]})
    assert r.status_code == 401


async def test_duplicate_email_rejected(client):
    parent = await make_parent(client)
    r = await client.post(
        "/api/v1/auth/register",
        json={"email": parent["email"], "full_name": "Again", "password": PASSWORD},
    )
    assert r.status_code == 409


async def test_children_listed_without_pin(client, family):
    r = await client.get("/api/v1/family/children", headers=family["parent_auth"])
    assert r.status_code == 200
    kids = r.json()["children"]
    assert [k["display_name"] for k in kids] == ["Amira", "Zayd"]
    assert all("pin" not in k and "pin_hash" not in k for k in kids)


async def test_child_validation(client, family):
    for bad in (
        {"display_name": "X", "school_year": 9, "pin": "1234"},
        {"display_name": "X", "school_year": 3, "pin": "12"},
        {"display_name": "X", "school_year": 3, "pin": "abcd"},
        {"display_name": "", "school_year": 3, "pin": "1234"},
    ):
        r = await client.post("/api/v1/family/children", headers=family["parent_auth"], json=bad)
        assert r.status_code == 422, bad


async def test_wrong_pin_then_lockout(client):
    parent = await make_parent(client)
    kid = await make_child(client, parent["access_token"], pin="4321")
    url = f"/api/v1/family/children/{kid['id']}/session"
    auth = bearer(parent["access_token"])
    for _ in range(5):
        r = await client.post(url, headers=auth, json={"pin": "0000"})
        assert r.status_code == 403
    # Locked now, even with the right PIN.
    r = await client.post(url, headers=auth, json={"pin": "4321"})
    assert r.status_code == 429
    # The parent resets the PIN, which clears the lock.
    r = await client.patch(f"/api/v1/family/children/{kid['id']}", headers=auth, json={"pin": "1111"})
    assert r.status_code == 200
    r = await client.post(url, headers=auth, json={"pin": "1111"})
    assert r.status_code == 200


async def test_two_children_have_separate_records(client, family):
    r = await client.post("/api/v1/gamification/award-xp", headers=family["a_auth"], json={"amount": 40, "reason": "test"})
    assert r.status_code == 200
    a = (await client.get("/api/v1/gamification/profile", headers=family["a_auth"])).json()
    b = (await client.get("/api/v1/gamification/profile", headers=family["b_auth"])).json()
    assert a["user_id"] == family["a"]["id"] and b["user_id"] == family["b"]["id"]
    assert a["xp"] >= 40
    assert b["xp"] == 0


async def test_mastery_survives_a_restart(client, family):
    from backend.bkt_lite import bkt_lite

    r = await client.post(
        "/api/v1/ai-models/bkt/predict",
        headers=family["a_auth"],
        json={"skill_id": "fractions", "skill_name": "Fractions", "attempts": 4, "successes": 4},
    )
    assert r.status_code == 200, r.text
    saved = r.json()["mastery_probability"]
    assert saved > 0.3

    bkt_lite.student_states.clear()  # what a restart does to memory

    r = await client.post(
        "/api/v1/ai-models/bkt/predict",
        headers=family["a_auth"],
        json={"skill_id": "fractions", "skill_name": "Fractions", "attempts": 0, "successes": 0},
    )
    assert abs(r.json()["mastery_probability"] - saved) < 1e-3

    # The sibling's record is untouched.
    r = await client.post(
        "/api/v1/ai-models/bkt/predict",
        headers=family["b_auth"],
        json={"skill_id": "fractions", "skill_name": "Fractions", "attempts": 0, "successes": 0},
    )
    assert r.json()["mastery_probability"] < saved


async def test_parent_sees_own_children_only(client, family):
    r = await client.get(f"/api/v1/parent/weekly-report/{family['a']['id']}", headers=family["parent_auth"])
    assert r.status_code == 200

    other = await make_parent(client)
    r = await client.get(f"/api/v1/parent/weekly-report/{family['a']['id']}", headers=bearer(other["access_token"]))
    assert r.status_code == 404
    # ...and cannot start a session as someone else's child, even with the right PIN.
    r = await client.post(
        f"/api/v1/family/children/{family['a']['id']}/session",
        headers=bearer(other["access_token"]),
        json={"pin": "1234"},
    )
    assert r.status_code == 404


async def test_roles_do_not_cross(client, family):
    # A child's session cannot manage the family or read parent reports.
    r = await client.get("/api/v1/family/children", headers=family["a_auth"])
    assert r.status_code == 403
    r = await client.get(f"/api/v1/parent/weekly-report/{family['b']['id']}", headers=family["a_auth"])
    assert r.status_code == 403
    # A parent's token cannot be used as a learner.
    r = await client.get("/api/v1/gamification/profile", headers=family["parent_auth"])
    assert r.status_code == 403
