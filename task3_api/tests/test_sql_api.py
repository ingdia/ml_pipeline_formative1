"""Tests for the PostgreSQL measurement endpoints.

A real PostgreSQL instance is not required: psycopg2's connection is faked
so the tests exercise routing, status codes and error handling in isolation.
"""
from unittest.mock import patch

import psycopg2
import pytest
from fastapi.testclient import TestClient

from task3_api.main import app

client = TestClient(app)


class FakeCursor:
    def __init__(self, fetchone_result=None, fetchall_result=None, rowcount=0, raises=None):
        self.fetchone_result = fetchone_result
        self.fetchall_result = fetchall_result or []
        self.rowcount = rowcount
        self.raises = raises
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if self.raises:
            raise self.raises

    def fetchone(self):
        return self.fetchone_result

    def fetchall(self):
        return self.fetchall_result

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeConnection:
    def __init__(self, cursor: FakeCursor):
        self._cursor = cursor
        self.committed = False
        self.rolled_back = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True

    def close(self):
        pass


def _patched(cursor: FakeCursor):
    return patch("task3_api.sql_routes.get_pg_connection", return_value=FakeConnection(cursor))


MEASUREMENT = {
    "station_id": 1,
    "parameter_id": 1,
    "measured_at": "2004-03-10T18:00:00",
    "value": 2.6,
}


def test_create_measurement():
    with _patched(FakeCursor(fetchone_result=MEASUREMENT)):
        r = client.post("/sql/measurements", json=MEASUREMENT)
    assert r.status_code == 201
    assert r.json()["value"] == 2.6


def test_create_measurement_conflict():
    with _patched(FakeCursor(raises=psycopg2.errors.UniqueViolation())):
        r = client.post("/sql/measurements", json=MEASUREMENT)
    assert r.status_code == 409


def test_list_measurements():
    with _patched(FakeCursor(fetchall_result=[MEASUREMENT])):
        r = client.get("/sql/measurements", params={"station_id": 1})
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_latest_measurement_found():
    with _patched(FakeCursor(fetchone_result=MEASUREMENT)):
        r = client.get("/sql/measurements/latest")
    assert r.status_code == 200


def test_latest_measurement_not_found():
    with _patched(FakeCursor(fetchone_result=None)):
        r = client.get("/sql/measurements/latest")
    assert r.status_code == 404


def test_range_rejects_end_before_start():
    r = client.get(
        "/sql/measurements/range",
        params={"start": "2004-03-10T18:00:00", "end": "2004-03-01T00:00:00"},
    )
    assert r.status_code == 400


def test_range_returns_rows():
    with _patched(FakeCursor(fetchall_result=[MEASUREMENT])):
        r = client.get(
            "/sql/measurements/range",
            params={"start": "2004-01-01T00:00:00", "end": "2005-01-01T00:00:00"},
        )
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_get_measurement_not_found():
    with _patched(FakeCursor(fetchone_result=None)):
        r = client.get("/sql/measurements/1/1/2004-03-10T18:00:00")
    assert r.status_code == 404


def test_update_measurement():
    updated = {**MEASUREMENT, "value": 9.9}
    with _patched(FakeCursor(fetchone_result=updated)):
        r = client.put("/sql/measurements/1/1/2004-03-10T18:00:00", json={"value": 9.9})
    assert r.status_code == 200
    assert r.json()["value"] == 9.9


def test_update_measurement_not_found():
    with _patched(FakeCursor(fetchone_result=None)):
        r = client.put("/sql/measurements/1/1/2004-03-10T18:00:00", json={"value": 9.9})
    assert r.status_code == 404


def test_delete_measurement():
    with _patched(FakeCursor(rowcount=1)):
        r = client.delete("/sql/measurements/1/1/2004-03-10T18:00:00")
    assert r.status_code == 204


def test_delete_measurement_not_found():
    with _patched(FakeCursor(rowcount=0)):
        r = client.delete("/sql/measurements/1/1/2004-03-10T18:00:00")
    assert r.status_code == 404
