"""CRUD and query endpoints for the PostgreSQL `measurements` fact table.

Schema: task2_databases/sql/01_schema.sql
    measurements(station_id, parameter_id, measured_at, value)
    PRIMARY KEY (station_id, parameter_id, measured_at)
"""
from contextlib import contextmanager
from datetime import datetime
from typing import Optional

import psycopg2
from fastapi import APIRouter, HTTPException, Query, status

from .db import get_pg_connection
from .schemas import MeasurementCreate, MeasurementOut, MeasurementUpdate

router = APIRouter(prefix="/sql/measurements", tags=["SQL - measurements"])


@contextmanager
def _connection():
    try:
        conn = get_pg_connection()
    except psycopg2.OperationalError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, f"PostgreSQL unavailable: {exc}")
    try:
        yield conn
    finally:
        conn.close()


def _fetch_one(cur, station_id: int, parameter_id: int, measured_at: datetime):
    cur.execute(
        "SELECT station_id, parameter_id, measured_at, value FROM measurements "
        "WHERE station_id = %s AND parameter_id = %s AND measured_at = %s",
        (station_id, parameter_id, measured_at),
    )
    return cur.fetchone()


@router.post("", response_model=MeasurementOut, status_code=status.HTTP_201_CREATED)
def create_measurement(body: MeasurementCreate):
    with _connection() as conn, conn.cursor() as cur:
        try:
            cur.execute(
                "INSERT INTO measurements (station_id, parameter_id, measured_at, value) "
                "VALUES (%s, %s, %s, %s) "
                "RETURNING station_id, parameter_id, measured_at, value",
                (body.station_id, body.parameter_id, body.measured_at, body.value),
            )
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            raise HTTPException(status.HTTP_409_CONFLICT, "A measurement already exists for this station, parameter and time")
        except psycopg2.errors.ForeignKeyViolation:
            conn.rollback()
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown station_id or parameter_id")
        row = cur.fetchone()
        conn.commit()
        return row


@router.get("", response_model=list[MeasurementOut])
def list_measurements(
    station_id: Optional[int] = None,
    parameter_id: Optional[int] = None,
    limit: int = Query(100, ge=1, le=1000),
):
    sql = "SELECT station_id, parameter_id, measured_at, value FROM measurements WHERE 1=1"
    params: list = []
    if station_id is not None:
        sql += " AND station_id = %s"
        params.append(station_id)
    if parameter_id is not None:
        sql += " AND parameter_id = %s"
        params.append(parameter_id)
    sql += " ORDER BY measured_at DESC LIMIT %s"
    params.append(limit)
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@router.get("/latest", response_model=MeasurementOut)
def latest_measurement(
    station_id: Optional[int] = None,
    parameter_id: Optional[int] = None,
):
    sql = "SELECT station_id, parameter_id, measured_at, value FROM measurements WHERE 1=1"
    params: list = []
    if station_id is not None:
        sql += " AND station_id = %s"
        params.append(station_id)
    if parameter_id is not None:
        sql += " AND parameter_id = %s"
        params.append(parameter_id)
    sql += " ORDER BY measured_at DESC LIMIT 1"
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No measurements found")
    return row


@router.get("/range", response_model=list[MeasurementOut])
def measurements_by_range(
    start: datetime,
    end: datetime,
    station_id: Optional[int] = None,
    parameter_id: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=10000),
):
    if end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end must not be before start")
    sql = (
        "SELECT station_id, parameter_id, measured_at, value FROM measurements "
        "WHERE measured_at BETWEEN %s AND %s"
    )
    params: list = [start, end]
    if station_id is not None:
        sql += " AND station_id = %s"
        params.append(station_id)
    if parameter_id is not None:
        sql += " AND parameter_id = %s"
        params.append(parameter_id)
    sql += " ORDER BY measured_at LIMIT %s"
    params.append(limit)
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@router.get("/{station_id}/{parameter_id}/{measured_at}", response_model=MeasurementOut)
def get_measurement(station_id: int, parameter_id: int, measured_at: datetime):
    with _connection() as conn, conn.cursor() as cur:
        row = _fetch_one(cur, station_id, parameter_id, measured_at)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measurement not found")
    return row


@router.put("/{station_id}/{parameter_id}/{measured_at}", response_model=MeasurementOut)
def update_measurement(station_id: int, parameter_id: int, measured_at: datetime, body: MeasurementUpdate):
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(
            "UPDATE measurements SET value = %s "
            "WHERE station_id = %s AND parameter_id = %s AND measured_at = %s "
            "RETURNING station_id, parameter_id, measured_at, value",
            (body.value, station_id, parameter_id, measured_at),
        )
        row = cur.fetchone()
        conn.commit()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measurement not found")
    return row


@router.delete("/{station_id}/{parameter_id}/{measured_at}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement(station_id: int, parameter_id: int, measured_at: datetime):
    with _connection() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM measurements WHERE station_id = %s AND parameter_id = %s AND measured_at = %s",
            (station_id, parameter_id, measured_at),
        )
        deleted = cur.rowcount
        conn.commit()
    if deleted == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Measurement not found")
