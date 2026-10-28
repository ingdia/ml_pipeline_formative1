-- Air Quality (UCI) – relational schema, PostgreSQL
DROP TABLE IF EXISTS measurements, parameters, stations CASCADE;

-- 1. Where the readings come from
CREATE TABLE stations (
    station_id    SERIAL PRIMARY KEY,
    station_name  VARCHAR(100) NOT NULL UNIQUE,
    country       VARCHAR(50)  NOT NULL,
    setting       VARCHAR(150),
    first_reading TIMESTAMP,
    last_reading  TIMESTAMP
);

-- 2. What is being measured (lookup / dimension table)
CREATE TABLE parameters (
    parameter_id  SERIAL PRIMARY KEY,
    code          VARCHAR(20)  NOT NULL UNIQUE,   -- original CSV column name
    description   VARCHAR(100) NOT NULL,
    unit          VARCHAR(20),
    category      VARCHAR(20)  NOT NULL
                  CHECK (category IN ('reference','sensor','weather')),
    pollutant     VARCHAR(20)                     -- CO, NMHC, C6H6, NOx, NO2, O3 or NULL
);

-- 3. Fact table: one row per station / parameter / hour
CREATE TABLE measurements (
    station_id    INT       NOT NULL REFERENCES stations(station_id),
    parameter_id  INT       NOT NULL REFERENCES parameters(parameter_id),
    measured_at   TIMESTAMP NOT NULL,
    value         NUMERIC(10,4) NOT NULL,
    PRIMARY KEY (station_id, parameter_id, measured_at)
);

CREATE INDEX idx_meas_time        ON measurements (measured_at);
CREATE INDEX idx_meas_param_time  ON measurements (parameter_id, measured_at);
