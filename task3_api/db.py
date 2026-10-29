"""Connection helpers for the Task 3 CRUD API.

PostgreSQL: reads DATABASE_URL (same database loaded in task2_databases/sql).
MongoDB: reads MONGO_URI (same database loaded in task2_databases/mongodb).
If MONGO_URI is not set, falls back to the in-memory mongomock emulator so the
API can be run and demoed without a live Atlas/MongoDB instance, matching the
convention used by task2_databases/mongodb/05_mongo_load_and_queries.py.
"""
import os

import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.environ.get(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/airquality"
)
MONGO_URI = os.environ.get("MONGO_URI")
MONGO_DB_NAME = os.environ.get("MONGO_DB_NAME", "airquality")
MONGO_COLLECTION_NAME = os.environ.get("MONGO_COLLECTION_NAME", "readings")

_mongo_client = None


def get_pg_connection():
    """Open a new PostgreSQL connection with dict-like row access.

    A fresh connection per request keeps the API stateless and simple; the
    dataset and endpoint volume here do not warrant a pooling layer.
    """
    return psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)


def get_mongo_collection():
    """Return the MongoDB readings collection, real or mocked."""
    global _mongo_client
    if _mongo_client is None:
        if MONGO_URI:
            from pymongo import MongoClient

            _mongo_client = MongoClient(MONGO_URI)
        else:
            import mongomock

            _mongo_client = mongomock.MongoClient()
    return _mongo_client[MONGO_DB_NAME][MONGO_COLLECTION_NAME]
