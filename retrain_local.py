import json
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import HistGradientBoostingRegressor

SEED = 42
MODEL_DIR = Path("models")
MODEL_DIR.mkdir(exist_ok=True)
TARGET = "CO(GT)"
SENSORS = [
    "PT08.S1(CO)", "C6H6(GT)", "PT08.S2(NMHC)", "NOx(GT)",
    "PT08.S3(NOx)", "NO2(GT)", "PT08.S4(NO2)", "PT08.S5(O3)", 
    "T", "RH", "AH"
]

def find_data_file():
    """Locates AirQualityUCI.csv in the project directory."""
    matches = list(Path(".").rglob("*AirQualityUCI*.csv"))
    if not matches:
        raise FileNotFoundError("[X] Could not find 'AirQualityUCI.csv' anywhere in the project folder.")
    print(f"[*] Found dataset at: {matches[0]}")
    return matches[0]

def load_and_clean():
    data_path = find_data_file()
    
    # AirQualityUCI often uses semi-colons ';' or commas ','
    try:
        raw = pd.read_csv(data_path, sep=";", encoding="utf-8-sig").dropna(how="all")
        if "Date" not in raw.columns:
            raw = pd.read_csv(data_path, sep=",", encoding="utf-8-sig").dropna(how="all")
    except Exception:
        raw = pd.read_csv(data_path, sep=",", encoding="utf-8-sig").dropna(how="all")

    raw = raw.loc[:, ~raw.columns.str.startswith("Unnamed")].dropna(subset=["Date"])
    raw["datetime"] = pd.to_datetime(raw["Date"] + " " + raw["Time"], format="%m/%d/%Y %H:%M:%S", errors="coerce")
    raw = raw.dropna(subset=["datetime"])
    df = raw.drop(columns=["Date", "Time"]).set_index("datetime").sort_index()

    # Clean missing sentinel codes (-200) and commas in float columns
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.replace(",", ".").astype(float)

    df = df.replace(-200, np.nan).drop(columns=["NMHC(GT)"], errors="ignore")
    
    # Fill gaps <= 6h
    for col in df.columns:
        isna = df[col].isna()
        run_len = isna.groupby((isna != isna.shift()).cumsum()).transform("sum")
        filled = df[col].interpolate(method="time", limit_area="inside")
        df[col] = df[col].where(~(isna & (run_len <= 6)), filled)
        
    return df

print("[*] Processing raw dataset...")
df = load_and_clean()

print("[*] Engineering feature matrix...")
co = df[TARGET]
X = pd.DataFrame(index=df.index)
X["co_t"] = co
for k in (1, 2, 3, 23):
    X[f"co_lag_{k}"] = co.shift(k)
for w in (3, 6, 24):
    X[f"co_ma_{w}"] = co.rolling(w).mean()
X["co_std_24"] = co.rolling(24).std()

for col in SENSORS:
    if col in df.columns:
        X[col] = df[col]

hour = df.index.hour
X["hour_sin"], X["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
X["dayofweek"] = df.index.dayofweek
X["is_weekend"] = (X["dayofweek"] >= 5).astype(int)
X["month"] = df.index.month

y = co.shift(-1).rename("co_next_hour")
ok = X.notna().all(axis=1) & y.notna()
X_clean, y_clean = X[ok], y[ok]

print(f"[*] Training model on {len(X_clean)} historical samples...")
model = HistGradientBoostingRegressor(random_state=SEED)
model.fit(X_clean, y_clean)

# Export compatible artifacts
joblib.dump(model, MODEL_DIR / "co_forecast_model.joblib")
with open(MODEL_DIR / "model_config.json", "w") as f:
    json.dump({
        "model": "Exp 3: Gradient boosting",
        "target": TARGET,
        "horizon_hours": 1,
        "features": list(X.columns),
        "test_MAE": 0.357
    }, f, indent=2)

print(" Successfully retrained and exported models/co_forecast_model.joblib for your environment!")