import pytest
from fastapi.testclient import TestClient

import ai
from main import app

VALID = {
    "name": "Test Student",
    "date_of_birth": "2005-05-05",
    "email": "test@example.com",
    "course": "Python",
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDENTS_DB_PATH", str(tmp_path / "test.db"))
    with TestClient(app) as c:      # context manager runs the startup (creates tables)
        yield c


def make(client, **overrides):
    return client.post("/students", json={**VALID, **overrides})


def test_create_and_get(client):
    r = make(client)
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1 and body["email"] == "test@example.com"
    assert client.get("/students/1").json()["name"] == "Test Student"


def test_list_and_filters(client):
    make(client)
    make(client, name="Second One", email="two@example.com", date_of_birth="2007-01-01", course="Data Science")
    assert len(client.get("/students").json()) == 2
    assert len(client.get("/students", params={"course": "Data"}).json()) == 1
    assert len(client.get("/students", params={"name": "second"}).json()) == 1
    assert len(client.get("/students", params={"born_after": "2006-01-01"}).json()) == 1
    assert len(client.get("/students", params={"limit": 1}).json()) == 1


def test_get_missing_returns_404(client):
    assert client.get("/students/999").status_code == 404


def test_put_replaces(client):
    make(client)
    r = client.put("/students/1", json={**VALID, "name": "Changed Name", "course": None})
    assert r.status_code == 200
    assert r.json()["name"] == "Changed Name" and r.json()["course"] is None


def test_patch_updates_only_sent_fields(client):
    make(client)
    r = client.patch("/students/1", json={"course": "Web Development"})
    assert r.status_code == 200
    assert r.json()["course"] == "Web Development" and r.json()["name"] == "Test Student"


def test_update_missing_returns_404(client):
    assert client.patch("/students/42", json={"course": "X"}).status_code == 404
    assert client.put("/students/42", json=VALID).status_code == 404


def test_delete(client):
    make(client)
    assert client.delete("/students/1").status_code == 204
    assert client.get("/students/1").status_code == 404
    assert client.delete("/students/1").status_code == 404


def test_validation_errors(client):
    assert make(client, name="A").status_code == 422                      # too short
    assert make(client, email="not-an-email").status_code == 422
    assert make(client, date_of_birth="2999-01-01").status_code == 422     # future date
    assert client.post("/students", json={"name": "No Contact", "date_of_birth": "2005-01-01"}).status_code == 422
    assert client.patch("/students/1", json={}).status_code == 422


def test_duplicate_email_returns_409(client):
    assert make(client).status_code == 201
    assert make(client).status_code == 409


def test_ai_endpoint_uses_records_as_context(client, monkeypatch):
    make(client)
    captured = {}

    def fake_ollama(prompt):
        captured["prompt"] = prompt
        return "There is 1 student."

    monkeypatch.setattr(ai, "ask_ollama", fake_ollama)
    r = client.post("/ai/ask", json={"question": "How many students are there?"})
    assert r.status_code == 200 and r.json()["answer"] == "There is 1 student."
    assert "Total students in database: 1" in captured["prompt"]
    assert "test@example.com" not in captured["prompt"]    # contact info is never sent to the model
