\echo '--- Q1: Range filter: reference CO, NO2 and temperature for 11 Mar 2004, 06:00-10:00 (morning rush)'
SELECT m.measured_at,
       MAX(m.value) FILTER (WHERE p.code='CO(GT)')  AS co_mg_m3,
       MAX(m.value) FILTER (WHERE p.code='NO2(GT)') AS no2_ug_m3,
       MAX(m.value) FILTER (WHERE p.code='T')       AS temp_c
FROM measurements m JOIN parameters p USING (parameter_id)
WHERE m.measured_at BETWEEN '2004-03-11 06:00' AND '2004-03-11 10:00'
GROUP BY m.measured_at ORDER BY m.measured_at;

\echo '--- Q2: Monthly average of reference pollutants (aggregation)'
SELECT to_char(date_trunc('month', m.measured_at),'YYYY-MM') AS month,
       ROUND(AVG(m.value) FILTER (WHERE p.code='CO(GT)'),2)   AS avg_co,
       ROUND(AVG(m.value) FILTER (WHERE p.code='C6H6(GT)'),2) AS avg_benzene,
       ROUND(AVG(m.value) FILTER (WHERE p.code='NO2(GT)'),1)  AS avg_no2
FROM measurements m JOIN parameters p USING (parameter_id)
GROUP BY 1 ORDER BY 1;

\echo '--- Q3: Top 5 most polluted days by average NO2 (days with >=18 valid hours)'
SELECT m.measured_at::date AS day, ROUND(AVG(m.value),1) AS avg_no2, COUNT(*) AS valid_hours
FROM measurements m JOIN parameters p USING (parameter_id)
WHERE p.code='NO2(GT)'
GROUP BY 1 HAVING COUNT(*) >= 18
ORDER BY avg_no2 DESC LIMIT 5;

\echo '--- Q4: Average CO by hour of day (daily traffic pattern)'
SELECT EXTRACT(HOUR FROM m.measured_at)::int AS hour, ROUND(AVG(m.value),2) AS avg_co
FROM measurements m JOIN parameters p USING (parameter_id)
WHERE p.code='CO(GT)'
GROUP BY 1 ORDER BY 1;

\echo '--- Q5: Valid readings per parameter (data-quality check)'
SELECT p.code, p.category, COUNT(m.value) AS valid_rows,
       9357 - COUNT(m.value) AS missing_rows,
       ROUND(100.0*(9357 - COUNT(m.value))/9357,1) AS pct_missing
FROM parameters p LEFT JOIN measurements m USING (parameter_id)
GROUP BY p.parameter_id, p.code, p.category ORDER BY p.parameter_id;
