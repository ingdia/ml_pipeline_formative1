"""CRUD and query endpoints for the MongoDB `readings` collection.

Document shape: task2_databases/mongodb/05_mongo_load_and_queries.py
    {timestamp, station, reference?, sensors?, weather?}
"""
from datetime import datetime
from typing import Optional

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, HTTPException, Query, status
from pymongo import ReturnDocument

from .db import get_mongo_collection
from .schemas import ReadingCreate, ReadingOut, ReadingUpdate

router = APIRouter(prefix="/mongo/readings", tags=["MongoDB - readings"])


def _to_out(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _object_id(reading_id: str) -> ObjectId:
    try:
        return ObjectId(reading_id)
    except InvalidId:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid reading id")


@router.post("", response_model=ReadingOut, status_code=status.HTTP_201_CREATED)
def create_reading(body: ReadingCreate):
    col = get_mongo_collection()
    doc = body.model_dump(exclude_none=True)
    result = col.insert_one(doc)
    doc["_id"] = result.inserted_id
    return _to_out(doc)


@router.get("", response_model=list[ReadingOut])
def list_readings(limit: int = Query(100, ge=1, le=1000)):
    col = get_mongo_collection()
    cursor = col.find().sort("timestamp", -1).limit(limit)
    return [_to_out(d) for d in cursor]


@router.get("/latest", response_model=ReadingOut)
def latest_reading():
    col = get_mongo_collection()
    doc = next(iter(col.find().sort("timestamp", -1).limit(1)), None)
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No readings found")
    return _to_out(doc)


@router.get("/range", response_model=list[ReadingOut])
def readings_by_range(
    start: datetime,
    end: datetime,
    limit: int = Query(1000, ge=1, le=10000),
):
    if end < start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "end must not be before start")
    col = get_mongo_collection()
    cursor = col.find({"timestamp": {"$gte": start, "$lte": end}}).sort("timestamp", 1).limit(limit)
    return [_to_out(d) for d in cursor]


@router.get("/{reading_id}", response_model=ReadingOut)
def get_reading(reading_id: str):
    col = get_mongo_collection()
    doc = col.find_one({"_id": _object_id(reading_id)})
    if doc is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")
    return _to_out(doc)


@router.put("/{reading_id}", response_model=ReadingOut)
def update_reading(reading_id: str, body: ReadingUpdate):
    col = get_mongo_collection()
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    oid = _object_id(reading_id)
    result = col.find_one_and_update(
        {"_id": oid}, {"$set": updates}, return_document=ReturnDocument.AFTER
    )
    if result is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")
    return _to_out(result)


@router.delete("/{reading_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reading(reading_id: str):
    col = get_mongo_collection()
    result = col.delete_one({"_id": _object_id(reading_id)})
    if result.deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Reading not found")
