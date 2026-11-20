"""The app starts, serves its pages, and answers honestly without a model key."""


async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"


async def test_pages_served(client):
    for path in ("/", "/account", "/parent"):
        r = await client.get(path)
        assert r.status_code == 200, path
        assert "<html" in r.text.lower(), path


async def test_home_page_has_no_invented_numbers(client):
    r = await client.get("/")
    assert "emotionHistory.push(50" not in r.text  # the old fake emotion history
    assert '<span class="skill-name">Addition</span>' not in r.text  # the old fake skills


async def test_schedule_today(client, family):
    r = await client.get("/api/v1/schedule/today", headers=family["a_auth"])
    assert r.status_code == 200
    assert r.json()["blocks"]


async def test_chat_without_model_key_says_so(client, family):
    r = await client.post(
        "/api/v1/chat/message",
        headers=family["a_auth"],
        json={"message": "What is 7 x 8?", "age": 8, "topic": "math"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["ai_powered"] is False
    assert "connection" in body["response"]
    assert body["bkt_update"] is None  # no mastery change when the tutor did not answer
