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


def test_meta_lan_ipv4(client: TestClient):
    r = client.get("/meta/lan-ipv4")
    assert r.status_code == 200
    data = r.json()
    assert "lan_ipv4" in data
    assert data["lan_ipv4"] is None or isinstance(data["lan_ipv4"], str)


def test_create_location(client: TestClient):
    r = client.post("/locations", json={"name": "Garage shelf", "color": "#ff5500"})
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Garage shelf"
    assert data["color"] == "#ff5500"
    assert "id" in data


def test_create_location_duplicate_name(client: TestClient):
    client.post("/locations", json={"name": "Dup", "color": "#111111"})
    r = client.post("/locations", json={"name": "dup", "color": "#222222"})
    assert r.status_code == 409


def test_list_locations(client: TestClient):
    client.post("/locations", json={"name": "Alpha", "color": "#0000ff"})
    client.post("/locations", json={"name": "Beta", "color": "#00ff00"})
    r = client.get("/locations")
    assert r.status_code == 200
    names = [x["name"] for x in r.json()]
    assert "Alpha" in names and "Beta" in names


def test_create_box(client: TestClient):
    loc = client.post("/locations", json={"name": "garage", "color": "#336699"})
    assert loc.status_code == 200
    lid = loc.json()["id"]
    r = client.post("/boxes", json={"label": "test_box_1", "location_id": lid})
    assert r.status_code == 200
    data = r.json()
    assert data["label"] == "test_box_1"
    assert data["location"] == "garage"
    assert data["location_id"] == lid
    assert data["location_color"] == "#336699"
    assert data["has_video"] is False
    assert "id" in data and "created_at" in data


def test_create_box_invalid_location_id(client: TestClient):
    r = client.post("/boxes", json={"label": "bad_loc", "location_id": 99999})
    assert r.status_code == 400


def test_create_box_duplicate_label(client: TestClient):
    client.post("/boxes", json={"label": "dup_label", "location": None})
    r = client.post("/boxes", json={"label": "dup_label", "location": None})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"]


def test_list_boxes(client: TestClient):
    la = client.post("/locations", json={"name": "a", "color": "#aaaaaa"})
    lb = client.post("/locations", json={"name": "b", "color": "#bbbbbb"})
    client.post("/boxes", json={"label": "list_a", "location_id": la.json()["id"]})
    client.post("/boxes", json={"label": "list_b", "location_id": lb.json()["id"]})
    r = client.get("/boxes")
    assert r.status_code == 200
    items = r.json()
    assert isinstance(items, list)
    labels = [b["label"] for b in items]
    assert "list_a" in labels and "list_b" in labels


def test_get_box(client: TestClient):
    loc = client.post("/locations", json={"name": "here", "color": "#cccccc"})
    create = client.post("/boxes", json={"label": "get_me", "location_id": loc.json()["id"]})
    assert create.status_code == 200
    bid = create.json()["id"]
    r = client.get(f"/boxes/{bid}")
    assert r.status_code == 200
    assert r.json()["label"] == "get_me"


def test_get_box_404(client: TestClient):
    r = client.get("/boxes/99999")
    assert r.status_code == 404


def test_patch_box(client: TestClient):
    old_l = client.post("/locations", json={"name": "old", "color": "#111111"})
    new_l = client.post("/locations", json={"name": "new", "color": "#222222"})
    create = client.post("/boxes", json={"label": "patch_me", "location_id": old_l.json()["id"]})
    bid = create.json()["id"]
    r = client.patch(f"/boxes/{bid}", json={"location_id": new_l.json()["id"]})
    assert r.status_code == 200
    assert r.json()["location"] == "new"
    assert r.json()["location_color"] == "#222222"


def test_patch_box_clear_location(client: TestClient):
    loc = client.post("/locations", json={"name": "x", "color": "#333333"})
    create = client.post("/boxes", json={"label": "clear_me", "location_id": loc.json()["id"]})
    bid = create.json()["id"]
    r = client.patch(f"/boxes/{bid}", json={"location_id": None})
    assert r.status_code == 200
    assert r.json()["location"] is None
    assert r.json()["location_id"] is None


def test_patch_box_label(client: TestClient):
    create = client.post("/boxes", json={"label": "rename_me"})
    assert create.status_code == 200
    bid = create.json()["id"]
    r = client.patch(f"/boxes/{bid}", json={"label": "renamed"})
    assert r.status_code == 200
    assert r.json()["label"] == "renamed"


def test_patch_box_label_duplicate(client: TestClient):
    b1 = client.post("/boxes", json={"label": "one"})
    b2 = client.post("/boxes", json={"label": "two"})
    bid2 = b2.json()["id"]
    r = client.patch(f"/boxes/{bid2}", json={"label": "one"})
    assert r.status_code == 409
    assert "already exists" in r.json()["detail"] or "already exists" in r.json()["detail"].lower()


def test_search_empty(client: TestClient):
    r = client.get("/search", params={"q": "wrench"})
    assert r.status_code == 200
    data = r.json()
    assert data["query"] == "wrench"
    assert data["results"] == []


def test_search_requires_q(client: TestClient):
    r = client.get("/search")
    assert r.status_code == 422  # validation error


def test_delete_box(client: TestClient):
    create = client.post("/boxes", json={"label": "to_delete"})
    assert create.status_code == 200
    bid = create.json()["id"]
    r = client.delete(f"/boxes/{bid}")
    assert r.status_code == 204
    r2 = client.get(f"/boxes/{bid}")
    assert r2.status_code == 404


def test_delete_box_404(client: TestClient):
    r = client.delete("/boxes/99999")
    assert r.status_code == 404
