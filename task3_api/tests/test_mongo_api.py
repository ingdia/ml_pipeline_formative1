"""Tests for the MongoDB reading endpoints, run against the mongomock
in-memory emulator (no MONGO_URI set, same fallback the API uses)."""
import pytest
from fastapi.testclient import TestClient

from task3_api import db
from task3_api.main import app

client = TestClient(app)

READING = {
    "timestamp": "2004-03-10T18:00:00Z",
    "station": {"station_id": 1, "name": "Italian city air-quality station"},
    "reference": {"co_mg_m3": 2.6},
}


@pytest.fixture(autouse=True)
def _fresh_collection():
    """Each test gets an empty collection in the shared mongomock client."""
    db.get_mongo_collection().delete_many({})
    yield


def _create():
    return client.post("/mongo/readings", json=READING)


def test_create_reading():
    r = _create()
    assert r.status_code == 201
    body = r.json()
    assert body["reference"]["co_mg_m3"] == 2.6
    assert "id" in body


def test_get_reading():
    rid = _create().json()["id"]
    r = client.get(f"/mongo/readings/{rid}")
    assert r.status_code == 200
    assert r.json()["id"] == rid


def test_get_reading_not_found():
    r = client.get("/mongo/readings/" + "a" * 24)
    assert r.status_code == 404


def test_get_reading_invalid_id():
    r = client.get("/mongo/readings/not-an-id")
    assert r.status_code == 400


def test_list_readings():
    _create()
    _create()
    r = client.get("/mongo/readings")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_latest_reading():
    _create()
    r = client.get("/mongo/readings/latest")
    assert r.status_code == 200


def test_latest_reading_empty():
    r = client.get("/mongo/readings/latest")
    assert r.status_code == 404


def test_range_rejects_end_before_start():
    r = client.get(
        "/mongo/readings/range",
        params={"start": "2004-03-10T00:00:00Z", "end": "2004-01-01T00:00:00Z"},
    )
    assert r.status_code == 400


def test_range_returns_matches():
    _create()
    r = client.get(
        "/mongo/readings/range",
        params={"start": "2004-01-01T00:00:00Z", "end": "2005-01-01T00:00:00Z"},
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_update_reading():
    rid = _create().json()["id"]
    r = client.put(f"/mongo/readings/{rid}", json={"reference": {"co_mg_m3": 9.9}})
    assert r.status_code == 200
    assert r.json()["reference"]["co_mg_m3"] == 9.9


def test_update_reading_no_fields():
    rid = _create().json()["id"]
    r = client.put(f"/mongo/readings/{rid}", json={})
    assert r.status_code == 400


def test_update_reading_not_found():
    r = client.put(f"/mongo/readings/{'a' * 24}", json={"reference": {"co_mg_m3": 1.0}})
    assert r.status_code == 404


def test_delete_reading():
    rid = _create().json()["id"]
    r = client.delete(f"/mongo/readings/{rid}")
    assert r.status_code == 204
    assert client.get(f"/mongo/readings/{rid}").status_code == 404


def test_delete_reading_not_found():
    r = client.delete(f"/mongo/readings/{'a' * 24}")
    assert r.status_code == 404
