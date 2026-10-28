// mongosh – run after loading data (e.g. python3 mongo_demo.py with MONGO_URI set)
use airquality

// Optional: native time-series collection (MongoDB 5.0+), one document per hourly reading
// db.createCollection("readings", { timeseries: { timeField: "timestamp", metaField: "station", granularity: "hours" } })

// Q1: range filter
db.readings.find(
  { timestamp: { $gte: ISODate("2004-03-11T06:00:00Z"), $lte: ISODate("2004-03-11T10:00:00Z") } },
  { _id: 0, timestamp: 1, "reference.co_mg_m3": 1, "reference.no2_ug_m3": 1, "weather.temp_c": 1 }
).sort({ timestamp: 1 })

// Q2: monthly averages
db.readings.aggregate([
  { $group: { _id: { $dateToString: { format: "%Y-%m", date: "$timestamp" } },
              avg_co: { $avg: "$reference.co_mg_m3" }, avg_benzene: { $avg: "$reference.benzene_ug_m3" },
              avg_no2: { $avg: "$reference.no2_ug_m3" } } },
  { $project: { _id: 0, month: "$_id", avg_co: { $round: ["$avg_co", 2] },
                avg_benzene: { $round: ["$avg_benzene", 2] }, avg_no2: { $round: ["$avg_no2", 1] } } },
  { $sort: { month: 1 } }
])

// Q3: top 5 days by average NO2 (>= 18 valid hours)
db.readings.aggregate([
  { $match: { "reference.no2_ug_m3": { $exists: true } } },
  { $group: { _id: { $dateToString: { format: "%Y-%m-%d", date: "$timestamp" } },
              avg_no2: { $avg: "$reference.no2_ug_m3" }, valid_hours: { $sum: 1 } } },
  { $match: { valid_hours: { $gte: 18 } } },
  { $sort: { avg_no2: -1 } }, { $limit: 5 },
  { $project: { _id: 0, day: "$_id", avg_no2: { $round: ["$avg_no2", 1] }, valid_hours: 1 } }
])

// Q4: average CO by hour of day
db.readings.aggregate([
  { $match: { "reference.co_mg_m3": { $exists: true } } },
  { $group: { _id: { $hour: "$timestamp" }, avg_co: { $avg: "$reference.co_mg_m3" } } },
  { $project: { _id: 0, hour: "$_id", avg_co: { $round: ["$avg_co", 2] } } },
  { $sort: { hour: 1 } }
])
