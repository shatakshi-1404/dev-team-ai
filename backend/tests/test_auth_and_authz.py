from tests.conftest import register


def test_register_login_me(client):
    h = register(client)
    assert client.get("/api/auth/me", headers=h).json()["email"] == "a@example.com"
    r = client.post("/api/auth/login", json={"email": "a@example.com", "password": "password123"})
    assert r.status_code == 200
    assert client.post("/api/auth/login", json={"email": "a@example.com", "password": "wrongpass1"}).status_code == 401


def test_duplicate_email_and_weak_password(client):
    register(client)
    assert (
        client.post("/api/auth/register", json={"email": "a@example.com", "password": "password123"}).status_code == 409
    )
    assert client.post("/api/auth/register", json={"email": "b@example.com", "password": "short"}).status_code == 422


def test_requires_auth(client):
    assert client.get("/api/projects").status_code == 401
    assert client.get("/api/projects", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_project_ownership_isolated(client):
    a, b = register(client, "a@example.com"), register(client, "b@example.com")
    pid = client.post("/api/projects", headers=a, json={"name": "p", "requirements": "x" * 30}).json()["id"]
    assert client.get(f"/api/projects/{pid}", headers=a).status_code == 200
    for method, url in (
        ("get", f"/api/projects/{pid}"),
        ("get", f"/api/projects/{pid}/files"),
        ("delete", f"/api/projects/{pid}"),
        ("post", f"/api/projects/{pid}/runs"),
    ):
        assert getattr(client, method)(url, headers=b).status_code == 404
    assert client.get("/api/projects", headers=b).json() == []


def test_system_status_without_key(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setattr(get_settings(), "groq_api_key", "")
    body = client.get("/api/system/status").json()
    assert body["llm_configured"] is False and "GROQ_API_KEY" in body["message"]
    pid = None
    h = register(client)
    pid = client.post("/api/projects", headers=h, json={"name": "p", "requirements": "x" * 30}).json()["id"]
    r = client.post(f"/api/projects/{pid}/runs", headers=h)
    assert r.status_code == 409 and r.json()["error"]["code"] == "llm_not_configured"
