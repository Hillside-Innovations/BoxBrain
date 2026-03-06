"""API tests: health, boxes CRUD, search. No video upload (needs ffmpeg + file)."""
import pytest
from fastapi.testclient import TestClient

# Import after conftest has set env so config uses temp dirs.
from main import app


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client: TestClient):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_create_box(client: TestClient):
    r = client.post("/boxes", json={"label": "test_box_1", "location": "garage"})
    assert r.status_code == 200
    data = r.json()
    assert data["label"] == "test_box_1"
    assert data["location"] == "garage"
    assert data["has_video"] is False
    assert "id" in data and "created_at" in data


def test_create_box_duplicate_label(client: TestClient):
    client.post("/boxes", json={"label": "dup_label", "location": None})
    r = client.post("/boxes", json={"label": "dup_label", "location": None})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_list_boxes(client: TestClient):
    client.post("/boxes", json={"label": "list_a", "location": "a"})
    client.post("/boxes", json={"label": "list_b", "location": "b"})
    r = client.get("/boxes")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    labels = [b["label"] for b in items]
    assert "list_a" in labels and "list_b" in labels


def test_get_box(client: TestClient):
    create = client.post("/boxes", json={"label": "get_me", "location": "here"})
    assert create.status_code == 200
    bid = create.json()["id"]
    r = client.get(f"/boxes/{bid}")
    assert r.status_code == 200
    assert r.json()["label"] == "get_me"


def test_get_box_404(client: TestClient):
    r = client.get("/boxes/99999")
    assert r.status_code == 404


def test_patch_box(client: TestClient):
    create = client.post("/boxes", json={"label": "patch_me", "location": "old"})
    bid = create.json()["id"]
    r = client.patch(f"/boxes/{bid}", json={"location": "new"})
    assert r.status_code == 200
    assert r.json()["location"] == "new"


def test_search_empty(client: TestClient):
    r = client.get("/search", params={"q": "wrench"})
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "wrench"
    assert data["results"] == []


def test_search_requires_q(client: TestClient):
    r = client.get("/search")
    assert r.status_code == 422  # validation error
