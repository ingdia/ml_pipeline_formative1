import os
import json
import joblib
import requests
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime

# ==========================================
# CONFIGURATION
# ==========================================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")
ENDPOINT_URL = f"{API_BASE_URL}/api/v1/readings/recent?limit=48"

MODEL_DIR = Path("models") if Path("models/co_forecast_model.joblib").exists() else Path("notebooks/models")
MODEL_PATH = MODEL_DIR / "co_forecast_model.joblib"
CONFIG_PATH = MODEL_DIR / "model_config.json"

TARGET = "CO(GT)"
MAX_GAP_HOURS = 6
SENSORS = [
    "PT08.S1(CO)", "C6H6(GT)", "PT08.S2(NMHC)", "NOx(GT)", 
    "PT08.S3(NOx)", "NO2(GT)", "PT08.S4(NO2)", "PT08.S5(O3)", 
    "T", "RH", "AH"
]


# ==========================================
# STEP 1: FETCH DATA FROM TASK 3 API
# ==========================================
def fetch_recent_data_from_api(endpoint_url: str) -> pd.DataFrame:
    """Queries Task 3 API for historical time-series records."""
    print(f"[*] Fetching records from API: {endpoint_url}")
    try:
        response = requests.get(endpoint_url, timeout=10)
        response.raise_for_status()
        records = response.json()

        if not records:
            raise ValueError("API returned an empty response.")

        df = pd.DataFrame(records)

        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime")
        elif "Date" in df.columns and "Time" in df.columns:
            df["datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%m/%d/%Y %H:%M:%S")
            df = df.drop(columns=["Date", "Time"]).set_index("datetime")

        df = df.sort_index()
        print(f"[✓] Successfully retrieved {len(df)} records ({df.index.min()} to {df.index.max()})")
        return df

    except Exception as e:
        raise ConnectionError(f"[X] API query failed: {e}")


# ==========================================
# STEP 2: REUSE TASK 1 PREPROCESSING
# ==========================================
def fill_short_gaps(s: pd.Series, max_gap: int = MAX_GAP_HOURS) -> pd.Series:
    """Interpolates gaps <= 6 hours."""
    isna = s.isna()
    run_len = isna.groupby((isna != isna.shift()).cumsum()).transform("sum")
    filled = s.interpolate(method="time", limit_area="inside")
    return s.where(~(isna & (run_len <= max_gap)), filled)


def clean_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    """Removes -200 sentinels and cleans short missing values."""
    df = raw_df.replace(-200, np.nan).drop(columns=["NMHC(GT)"], errors="ignore")
    return df.apply(fill_short_gaps, max_gap=MAX_GAP_HOURS)


def make_inference_features(clean_df: pd.DataFrame, expected_features: list) -> tuple[pd.DataFrame, pd.Timestamp]:
    """Engineers lags, moving averages, and cyclical features matching Task 1 training."""
    co = clean_df[TARGET]
    X = pd.DataFrame(index=clean_df.index)

    # Lags
    X["co_t"] = co
    for k in (1, 2, 3, 23):
        X[f"co_lag_{k}"] = co.shift(k)

    # Rolling averages & std
    for w in (3, 6, 24):
        X[f"co_ma_{w}"] = co.rolling(w).mean()
    X["co_std_24"] = co.rolling(24).std()

    # Sensor columns
    for col in SENSORS:
        if col in clean_df.columns:
            X[col] = clean_df[col]

    # Cyclical & Calendar features
    hour = clean_df.index.hour
    X["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    X["hour_cos"] = np.cos(2 * np.pi * hour / 24)
    X["dayofweek"] = clean_df.index.dayofweek
    X["is_weekend"] = (X["dayofweek"] >= 5).astype(int)
    X["month"] = clean_df.index.month

    latest_X = X.iloc[[-1]][expected_features]
    latest_timestamp = clean_df.index[-1]

    if latest_X.isna().any().any():
        nulls = latest_X.columns[latest_X.isna().any()].tolist()
        raise ValueError(f"[X] Null values present in columns: {nulls}. Provide more API historical records.")

    return latest_X, latest_timestamp


# ==========================================
# STEP 3 & 4: MODEL INFERENCE & OUTPUT
# ==========================================
def main():
    print("=" * 60)
    print("      TASK 4: FORECAST INTEGRATION PIPELINE      ")
    print("=" * 60)

    if not MODEL_PATH.exists() or not CONFIG_PATH.exists():
        raise FileNotFoundError(f"[X] Artifacts missing in '{MODEL_DIR}'. Ensure Task 1 notebook was executed.")

    model = joblib.load(MODEL_PATH)
    with open(CONFIG_PATH, "r") as f:
        config = json.load(f)

    print(f"[✓] Loaded Model: {config['model']}")

    raw_df = fetch_recent_data_from_api(ENDPOINT_URL)
    clean_df = clean_data(raw_df)
    X_latest, base_time = make_inference_features(clean_df, config["features"])

    prediction = model.predict(X_latest)[0]
    target_time = base_time + pd.Timedelta(hours=1)

    result = {
        "status": "SUCCESS",
        "execution_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "base_timestamp": str(base_time),
        "target_forecast_timestamp": str(target_time),
        "current_co_mg_m3": round(float(X_latest["co_t"].values[0]), 3),
        "predicted_co_next_hour_mg_m3": round(float(prediction), 3),
        "model_used": config["model"]
    }

    print("\n" + "=" * 60)
    print(json.dumps(result, indent=4))
    print("=" * 60)


if __name__ == "__main__":
    main()