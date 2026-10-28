"""Loads the Air Quality data into a MongoDB collection and runs 4 queries.
Uses a real MongoDB if MONGO_URI is set, otherwise the in-memory 'mongomock' emulator."""
import os, json, datetime as dt, pandas as pd
if os.environ.get("MONGO_URI"):
    from pymongo import MongoClient; client = MongoClient(os.environ["MONGO_URI"])
else:
    import mongomock; client = mongomock.MongoClient()
db = client["airquality"]; col = db["readings"]; col.drop()

df = pd.read_csv('AirQualityUCI.csv', encoding='utf-8-sig').dropna(how='all').iloc[:, :15]
ts = pd.to_datetime(df['Date']+' '+df['Time'], format='%m/%d/%Y %H:%M:%S')
groups = {"reference": {"CO(GT)":"co_mg_m3","NMHC(GT)":"nmhc_ug_m3","C6H6(GT)":"benzene_ug_m3","NOx(GT)":"nox_ppb","NO2(GT)":"no2_ug_m3"},
          "sensors":   {"PT08.S1(CO)":"co","PT08.S2(NMHC)":"nmhc","PT08.S3(NOx)":"nox","PT08.S4(NO2)":"no2","PT08.S5(O3)":"o3"},
          "weather":   {"T":"temp_c","RH":"rh_pct","AH":"abs_humidity"}}
station = {"station_id": 1, "name": "Italian city air-quality station", "country": "Italy"}
docs = []
for i, row in df.iterrows():
    d = {"timestamp": ts[i].to_pydatetime(), "station": station}
    for g, cols in groups.items():
        sub = {new: float(row[old]) for old, new in cols.items() if row[old] != -200}   # -200 = missing -> field omitted
        if sub: d[g] = sub
    docs.append(d)
col.insert_many(docs)
col.create_index("timestamp")
print("documents:", col.count_documents({}))
print("SAMPLE DOCUMENTS"); 
for d in col.find({}, {"_id":0}).limit(2): print(json.dumps(d, default=str, indent=2))

MOCK = not os.environ.get("MONGO_URI")
DIGITS = {"avg_co":2, "avg_benzene":2, "avg_no2":1}
def R(expr, n):   # $round is not implemented by mongomock, so it is applied in Python there
    return expr if MOCK else {"$round": [expr, n]}
def show(title, cur):
    print("\n--- "+title)
    for r in cur:
        if MOCK: r = {k: (round(v, DIGITS[k]) if k in DIGITS else v) for k, v in r.items()}
        print(json.dumps(r, default=str))
D = dt.datetime
show("Q1 range filter 2004-03-11 06:00-10:00", col.find(
    {"timestamp": {"$gte": D(2004,3,11,6), "$lte": D(2004,3,11,10)}},
    {"_id":0, "timestamp":1, "reference.co_mg_m3":1, "reference.no2_ug_m3":1, "weather.temp_c":1}).sort("timestamp",1))
show("Q2 monthly averages", col.aggregate([
    {"$group": {"_id": {"$dateToString": {"format":"%Y-%m","date":"$timestamp"}},
                "avg_co": {"$avg":"$reference.co_mg_m3"}, "avg_benzene": {"$avg":"$reference.benzene_ug_m3"},
                "avg_no2": {"$avg":"$reference.no2_ug_m3"}}},
    {"$project": {"_id":0, "month":"$_id", "avg_co":R("$avg_co",2),
                  "avg_benzene":R("$avg_benzene",2), "avg_no2":R("$avg_no2",1)}},
    {"$sort": {"month":1}}]))
show("Q3 top 5 days by avg NO2 (>=18 valid hours)", col.aggregate([
    {"$match": {"reference.no2_ug_m3": {"$exists": True}}},
    {"$group": {"_id": {"$dateToString": {"format":"%Y-%m-%d","date":"$timestamp"}},
                "avg_no2": {"$avg":"$reference.no2_ug_m3"}, "valid_hours": {"$sum":1}}},
    {"$match": {"valid_hours": {"$gte": 18}}},
    {"$sort": {"avg_no2": -1}}, {"$limit": 5},
    {"$project": {"_id":0, "day":"$_id", "avg_no2":R("$avg_no2",1), "valid_hours":1}}]))
show("Q4 average CO by hour of day", col.aggregate([
    {"$match": {"reference.co_mg_m3": {"$exists": True}}},
    {"$group": {"_id": {"$hour":"$timestamp"}, "avg_co": {"$avg":"$reference.co_mg_m3"}}},
    {"$project": {"_id":0, "hour":"$_id", "avg_co":R("$avg_co",2)}},
    {"$sort": {"hour":1}}]))
