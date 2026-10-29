"""Pydantic request/response models for the Task 3 CRUD API."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# SQL (PostgreSQL) - task2_databases.measurements
# One row per station, parameter and hour. See task2_databases/sql/01_schema.sql.
# ---------------------------------------------------------------------------
class MeasurementCreate(BaseModel):
    station_id: int
    parameter_id: int
    measured_at: datetime
    value: float


class MeasurementUpdate(BaseModel):
    value: float


class MeasurementOut(BaseModel):
    station_id: int
    parameter_id: int
    measured_at: datetime
    value: float


# ---------------------------------------------------------------------------
# MongoDB - task2_databases.readings
# One document per hourly reading, with nested reference/sensors/weather
# sub-documents. See task2_databases/mongodb/05_mongo_load_and_queries.py.
# ---------------------------------------------------------------------------
class ReadingCreate(BaseModel):
    timestamp: datetime
    station: dict
    reference: Optional[dict] = None
    sensors: Optional[dict] = None
    weather: Optional[dict] = None


class ReadingUpdate(BaseModel):
    timestamp: Optional[datetime] = None
    station: Optional[dict] = None
    reference: Optional[dict] = None
    sensors: Optional[dict] = None
    weather: Optional[dict] = None


class ReadingOut(ReadingCreate):
    id: str = Field(..., description="MongoDB ObjectId as a string")
