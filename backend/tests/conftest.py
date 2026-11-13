import os
import shutil
import tempfile

_tmp = tempfile.mkdtemp(prefix="devteam-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["WORKSPACE_ROOT"] = f"{_tmp}/workspaces"
os.environ["GROQ_API_KEY"] = "test-key-not-real"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-abcdefghij-xyz"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    shutil.rmtree(os.environ["WORKSPACE_ROOT"], ignore_errors=True)  # ids restart with the DB
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def client():
    return TestClient(app)


def register(client, email="a@example.com", password="password123"):
    r = client.post("/api/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def auth(client):
    return register(client)
