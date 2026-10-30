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
    
@app.get("/api/v1/readings/recent")
def get_mock_readings(limit: int = 48):
    import pandas as pd
    import numpy as np
    from pathlib import Path
    
    csv_path = Path("notebooks/data/AirQualityUCI.csv")
    if not csv_path.exists():
        csv_path = Path("data/AirQualityUCI.csv")
        
    try:
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig").dropna(how="all")
        if "Date" not in df.columns:
            df = pd.read_csv(csv_path, sep=",", encoding="utf-8-sig").dropna(how="all")
    except Exception:
        df = pd.read_csv(csv_path, sep=",", encoding="utf-8-sig").dropna(how="all")

    df = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(subset=["Date"]).head(limit)
    df = df.replace({np.nan: None})
    return df.to_dict(orient="records")