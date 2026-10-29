"""Task 3: CRUD and time-series query API for the Air Quality SQL and MongoDB
databases built in Task 2.

Run locally:
    uvicorn task3_api.main:app --reload
Then open http://127.0.0.1:8000/docs for interactive API docs.
"""
from fastapi import FastAPI

from .mongo_routes import router as mongo_router
from .sql_routes import router as sql_router

app = FastAPI(
    title="Air Quality CRUD API",
    description=(
        "CRUD and time-series query endpoints over the PostgreSQL measurements "
        "table and the MongoDB readings collection built in Task 2."
    ),
    version="1.0.0",
)

app.include_router(sql_router)
app.include_router(mongo_router)


@app.get("/", tags=["health"])
def health():
    return {"status": "ok"}
