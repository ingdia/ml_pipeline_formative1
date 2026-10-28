import numpy as np
import pandas as pd

TARGET = "CO(GT)"
MISSING_CODE = -200
MAX_GAP_HOURS = 6
DROPPED_COLUMNS = ["NMHC(GT)"]
SENSORS = ["PT08.S1(CO)", "C6H6(GT)", "PT08.S2(NMHC)", "NOx(GT)", "PT08.S3(NOx)", "NO2(GT)",
           "PT08.S4(NO2)", "PT08.S5(O3)", "T", "RH", "AH"]


def load_raw(path):
    df = pd.read_csv(path, encoding="utf-8-sig").dropna(how="all")
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")].dropna(subset=["Date"])
    df["datetime"] = pd.to_datetime(df["Date"] + " " + df["Time"], format="%m/%d/%Y %H:%M:%S")
    return df.drop(columns=["Date", "Time"]).set_index("datetime").sort_index()


def records_to_frame(records, time_key="datetime"):
    df = pd.DataFrame(records)
    df[time_key] = pd.to_datetime(df[time_key])
    df = df.set_index(time_key).sort_index()
    full = pd.date_range(df.index.min(), df.index.max(), freq="h")
    return df.reindex(full).rename_axis("datetime")


def fill_short_gaps(s, max_gap=MAX_GAP_HOURS):
    isna = s.isna()
    run_len = isna.groupby((isna != isna.shift()).cumsum()).transform("sum")
    filled = s.interpolate(method="time", limit_area="inside")
    return s.where(~(isna & (run_len <= max_gap)), filled)


def clean(raw_df, max_gap=MAX_GAP_HOURS):
    df = raw_df.replace(MISSING_CODE, np.nan).drop(columns=DROPPED_COLUMNS, errors="ignore")
    return df.apply(fill_short_gaps, max_gap=max_gap)


def make_features(clean_df, with_target=True):
    co = clean_df[TARGET]
    X = pd.DataFrame(index=clean_df.index)
    X["co_t"] = co
    for k in (1, 2, 3, 23):
        X[f"co_lag_{k}"] = co.shift(k)
    for w in (3, 6, 24):
        X[f"co_ma_{w}"] = co.rolling(w).mean()
    X["co_std_24"] = co.rolling(24).std()
    for col in SENSORS:
        X[col] = clean_df[col]
    hour = clean_df.index.hour
    X["hour_sin"], X["hour_cos"] = np.sin(2 * np.pi * hour / 24), np.cos(2 * np.pi * hour / 24)
    X["dayofweek"] = clean_df.index.dayofweek
    X["is_weekend"] = (X["dayofweek"] >= 5).astype(int)
    X["month"] = clean_df.index.month
    ok = X.notna().all(axis=1)
    if not with_target:
        return X[ok]
    y = co.shift(-1).rename("co_next_hour")
    ok &= y.notna()
    return X[ok], y[ok]
