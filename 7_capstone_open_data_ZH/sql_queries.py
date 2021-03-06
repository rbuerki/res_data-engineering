
import configparser

# CONFIG (return dwh configuration in ini format)
config = configparser.ConfigParser()
config.read_file(open('dwh.cfg'))

KEY = config.get("AWS", "KEY")
SECRET = config.get("AWS", "SECRET")
NON_MOT_LOC_DATA = config.get("S3", "NON_MOT_LOC_DATA")
NON_MOT_COUNT_DATA = config.get("S3", "NON_MOT_COUNT_DATA")
WEATHER_DATA = config.get("S3", "WEATHER_DATA")

TIME_DATA = config.get("S3", "TIME_DATA")
DATE_DATA = config.get("S3", "DATE_DATA")


# DROP TABLES

drop_fact_count = "DROP TABLE IF EXISTS fact_count;"
drop_fact_weather = "DROP TABLE IF EXISTS fact_weather;"
drop_dim_date = "DROP TABLE IF EXISTS dim_date CASCADE;"
drop_dim_location = "DROP TABLE IF EXISTS dim_location CASCADE;"
drop_dim_time = "DROP TABLE IF EXISTS dim_time CASCADE;"
drop_staging_NonMotCount = "DROP TABLE IF EXISTS staging_NonMotCount CASCADE;"
drop_staging_NonMotLocation = "DROP TABLE IF EXISTS staging_NonMotLocation CASCADE;"
drop_staging_weather = "DROP TABLE IF EXISTS staging_weather CASCADE;"


# CREATE TABLES

# Postgres' SERIAL command is not supported in Redshift. The equivalent is IDENTITY(0,1)
# Read more here: https://docs.aws.amazon.com/redshift/latest/dg/r_CREATE_TABLE_NEW.html

# Staging Tables

create_staging_NonMotCount = (
    """
    CREATE TABLE IF NOT EXISTS staging_NonMotCount(
        fk_zaehler VARCHAR(20),
        fk_standort SMALLINT,
        datum TIMESTAMP SORTKEY DISTKEY,
        velo_in SMALLINT,
        velo_out SMALLINT,
        fuss_in SMALLINT,
        fuss_out SMALLINT,
        ost INT,
        nord INT
    )
    DISTSTYLE KEY
    """
)

create_staging_NonMotLocation = (
    """
    CREATE TABLE IF NOT EXISTS staging_NonMotLocation(
        abkuerzung CHAR(8),
        bezeichnung VARCHAR(50),
        bis TIMESTAMP,
        fk_zaehler VARCHAR(20),
        id1 SMALLINT,
        richtung_in VARCHAR(50),
        richtung_out VARCHAR(50),
        von TIMESTAMP,
        objectid SMALLINT,
        korrekturfaktor FLOAT,
        long FLOAT,
        lat FLOAT
    )
    DISTSTYLE ALL
    """
)

create_staging_weather = (
    """
    CREATE TABLE IF NOT EXISTS staging_weather(
        datetime_cet TIMESTAMP SORTKEY,
        air_temperature FLOAT,
        humidity SMALLINT,
        wind_gust_max_10min FLOAT,
        wind_speed_avg_10min FLOAT,
        wind_force_avg_10min SMALLINT,
        wind_direction SMALLINT,
        windchill FLOAT,
        barometric_pressure_qfe FLOAT,
        dew_point FLOAT
    )
    DISTSTYLE AUTO
    """
)

# Dim Tables

create_dim_location = (
    """
    CREATE TABLE IF NOT EXISTS dim_location(
        location_key INT IDENTITY(0,1) PRIMARY KEY, -- counts_id SERIAL PRIMARY KEY,
        location_id SMALLINT NOT NULL,
        location_name VARCHAR(50) NOT NULL,
        location_code VARCHAR(8) NOT NULL,
        count_type CHAR(3) NOT NULL,
        lat FLOAT NOT NULL,
        long FLOAT NOT NULL,
        active_from DATE NOT NULL,
        active_to DATE
        -- still_active BOOLEAN NOT NULL
    )
    DISTSTYLE ALL
    """
)

create_dim_date = (
    """
    CREATE TABLE IF NOT EXISTS dim_date(
        date_key INT PRIMARY KEY SORTKEY,
        date DATE NOT NULL,
        year SMALLINT NOT NULL,
        quarter SMALLINT NOT NULL,
        month SMALLINT NOT NULL,
        month_name  VARCHAR(9) NOT NULL,
        week_of_year SMALLINT NOT NULL,
        day_of_year SMALLINT NOT NULL,
        day_of_quarter SMALLINT NOT NULL,
        day_of_month SMALLINT NOT NULL,
        day_of_week SMALLINT NOT NULL,
        day_name VARCHAR(9) NOT NULL,
        is_weekend BOOLEAN NOT NULL,
        is_holiday BOOLEAN NOT NULL,
        first_day_of_week DATE NOT NULL,
        last_day_of_week DATE NOT NULL,
        first_day_of_month DATE NOT NULL,
        last_day_of_month DATE NOT NULL,
        first_day_of_quarter DATE NOT NULL,
        last_day_of_quarter DATE NOT NULL,
        first_day_of_year DATE NOT NULL,
        last_day_of_year DATE NOT NULL
    )
    DISTSTYLE AUTO
    """
)

create_dim_time = (
    """
    CREATE TABLE IF NOT EXISTS dim_time(
        time_key INT PRIMARY KEY SORTKEY,
        time_of_day CHAR(5) NOT NULL,
        hour SMALLINT NOT NULL,
        half_hour CHAR(13) NOT NULL,
        quarter_hour CHAR(13) NOT NULL,
        minute SMALLINT NOT NULL
    )
    DISTSTYLE ALL
    """
)

# Fact Tables

create_fact_count = (
    """
    CREATE TABLE IF NOT EXISTS fact_count(
        counts_id INT IDENTITY(0,1) PRIMARY KEY, -- counts_id SERIAL PRIMARY KEY,
        date_key INT REFERENCES dim_date (date_key) SORTKEY DISTKEY,
        time_key INT REFERENCES dim_time (time_key),
        location_key SMALLINT REFERENCES dim_location (location_key),
        count_type CHAR(1),
        count_total SMALLINT,
        count_in SMALLINT,
        count_out SMALLINT
    )
    DISTSTYLE KEY
    """
)

create_fact_weather = (
    """
    CREATE TABLE IF NOT EXISTS fact_weather(
        weather_id INT IDENTITY(0,1) PRIMARY KEY,
        date_key INT REFERENCES dim_date (date_key) SORTKEY,
        time_key INT REFERENCES dim_time (time_key),
        air_temperature FLOAT,
        humidity SMALLINT,
        wind_gust_max FLOAT,
        wind_speed_avg FLOAT,
        wind_force_avg SMALLINT,
        wind_direction SMALLINT,
        windchill FLOAT,
        barometric_pressure_qfe FLOAT,
        dew_point FLOAT
    )
    DISTSTYLE AUTO
    """
)

# COPY INTO STAGING TABLES

# COPY loads data into a table from data files or from an Amazon DynamoDB table.
# Read more here: https://docs.aws.amazon.com/redshift/latest/dg/r_COPY.html

# copy_staging_NonMotLocation = (
#     f"""
#     COPY staging_NonMotLocation
#     FROM {LOC_DATA}
#     CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
#     FORMAT AS JSON {LOC_JSONPATH}
#     TIMEFORMAT 'auto'
#     TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
#     REGION 'eu-west-1';
#     """
# )

copy_staging_NonMotLocation = (
    f"""
    COPY staging_NonMotLocation
    FROM {NON_MOT_LOC_DATA}
    CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
    DELIMITER ','
    TIMEFORMAT 'YYYY-MM-DD HH:MI:SS'
    TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
    REGION 'eu-west-1';
    """
)

copy_staging_NonMotCount = (
    f"""
    COPY staging_nonMotCount
    FROM {NON_MOT_COUNT_DATA}
    CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
    DELIMITER ','
    TIMEFORMAT 'YYYY-MM-DD HH:MI:SS'
    TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
    REGION 'eu-west-1';
    """
)

# Redhsift does not support TIME datatype from PostgreSQL, so I have to import the data
copy_staging_weather = (
    f"""
    COPY staging_weather
    FROM {WEATHER_DATA}
    CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
    DELIMITER ','
    TIMEFORMAT 'YYYY-MM-DD HH:MI:SS'
    TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
    REGION 'eu-west-1';
    """
)

# Redhsift does not support TIME datatype from PostgreSQL, so I have to import the data
copy_dim_time = (
    f"""
    COPY dim_time
    FROM {TIME_DATA}
    CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
    DELIMITER ';'
    TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
    REGION 'eu-west-1';
    """
)

# Altough I was able to run the select statement for dim_date insert in Redshift
# the insertion did not work in the pipeline for whatever reason ...
copy_dim_date = (
    f"""
    COPY dim_date
    FROM {DATE_DATA}
    CREDENTIALS 'aws_access_key_id={KEY};aws_secret_access_key={SECRET}'
    DELIMITER ','
    TRUNCATECOLUMNS BLANKSASNULL EMPTYASNULL
    REGION 'eu-west-1';
    """
)

# INSERT INTO FINAL TABLES

# Note: I use DISTINCT statement to handle possible duplicates

insert_dim_location = (
    """
    INSERT INTO dim_location(
        location_id,
        location_name,
        location_code,
        count_type,
        long,
        lat,
        active_from,
        active_to
        -- still_active
    )
    SELECT
        DISTINCT sl.id1 AS location_id,
        sl.bezeichnung AS location_name,
        sl.abkuerzung AS location_code,
        LEFT(sl.abkuerzung, 1) AS count_type,
        sl.lat AS lat,
        sl.long AS long,
        sl.von AS active_from,
        sl.bis AS active_to
        -- CASE ??? AS still_active --------------- not implemented yet
    FROM staging_NonMotLocation as sl
    """
)

insert_fact_count = (
    """
    INSERT INTO fact_count(
        date_key,
        time_key,
        location_key,
        count_type,
        count_total,
        count_in,
        count_out
    )
    SELECT
        TO_CHAR(sc.datum,'yyyymmdd')::INT AS date_key,
        EXTRACT(HOUR FROM sc.datum)*100 + EXTRACT(MINUTE FROM sc.datum) AS time_key,
        sc.fk_standort AS location_key,
        dl.count_type AS count_type,
        sc.velo_in + sc.velo_out + sc.fuss_in + sc.fuss_out AS count_total,
        sc.velo_in + sc.fuss_in AS count_in,
        sc.velo_out + sc.fuss_out AS count_out
    FROM staging_NonMotCount AS sc
    JOIN dim_location AS dl
        ON dl.location_id = sc.fk_standort
    """
)

insert_fact_weather = (
    """
    INSERT INTO fact_weather(
        date_key,
        time_key,
        air_temperature,
        humidity,
        wind_gust_max,
        wind_speed_avg,
        wind_force_avg,
        wind_direction,
        windchill,
        barometric_pressure_qfe,
        dew_point
    )
    SELECT
        TO_CHAR(sw.datetime_cet,'yyyymmdd')::INT AS date_key,
        EXTRACT(HOUR FROM sw.datetime_cet)*100 + EXTRACT(MINUTE FROM sw.datetime_cet) AS time_key,
        sw.air_temperature AS air_temperature,
        sw.humidity AS humidity,
        sw.wind_gust_max_10min AS wind_gust_max,
        sw.wind_speed_avg_10min AS wind_speed_avg,
        sw.wind_force_avg_10min AS wind_force_avg,
        sw.wind_direction AS wind_direction,
        sw.windchill AS wind_chill,
        sw.barometric_pressure_qfe AS barometric_pressure_qfe,
        sw.dew_point AS dew_point
    FROM staging_weather AS sw
    """
)

# insert_dim_date = (
#     """
#     INSERT INTO dim_date
#     SELECT
#         TO_CHAR(datum,'yyyymmdd')::INT AS date_key,
#         datum AS date,
#         EXTRACT(year FROM datum) AS year,
#         EXTRACT(quarter FROM datum) AS quarter,
#         EXTRACT(MONTH FROM datum) AS month,
#         TO_CHAR(datum, 'Month') AS month_name,
#         EXTRACT(week FROM datum) AS week_of_year,
#         EXTRACT(doy FROM datum) AS day_of_year,
#         datum - DATE_TRUNC('quarter',datum)::DATE +1 AS day_of_quarter,
#         EXTRACT(DAY FROM datum) AS day_of_month,
#         EXTRACT(dow FROM datum)::INT AS day_of_week,
#         TO_CHAR(datum,'Day') AS day_name,
#         CASE
#             WHEN EXTRACT(dow FROM datum) IN (6,0) THEN TRUE
#             ELSE FALSE
#         END AS is_weekend,
#         CASE
#             WHEN to_char(datum, 'MMDD') IN
#                 ('0101', '0501', '0801', '1225', '1226') THEN TRUE
#             ELSE FALSE
#         END AS is_holiday,
#         datum +(1 -EXTRACT(dow FROM datum))::INT AS first_day_of_week,
#         datum +(7 -EXTRACT(dow FROM datum))::INT AS last_day_of_week,
#         datum +(1 -EXTRACT(DAY FROM datum))::INT AS first_day_of_month,
#         (DATE_TRUNC('MONTH',datum) +INTERVAL '1 MONTH - 1 day')::DATE AS last_day_of_month,
#         DATE_TRUNC('quarter',datum)::DATE AS first_day_of_quarter,
#         (DATE_TRUNC('quarter',datum) +INTERVAL '3 MONTH - 1 day')::DATE AS last_day_of_quarter,
#         TO_DATE(EXTRACT(year FROM datum) || '-01-01','YYYY-MM-DD') AS first_day_of_year,
#         TO_DATE(EXTRACT(year FROM datum) || '-12-31','YYYY-MM-DD') AS last_day_of_year
#     FROM (SELECT '2010-01-01'::DATE+ SEQUENCE.DAY AS datum
#         FROM GENERATE_SERIES (0, 5475) AS SEQUENCE (DAY)
#         GROUP BY SEQUENCE.DAY) DQ
#     ORDER BY 1
#     """
# )

# insert_dim_time = (
#     """
#     INSERT INTO dim_time
#     SELECT
#         EXTRACT(HOUR FROM MINUTE)*60 + EXTRACT(MINUTE FROM MINUTE) AS time_key,
#         to_char(MINUTE, 'hh24:mi') AS time_of_day,
#         EXTRACT(HOUR FROM MINUTE) AS hour,
#         to_char(MINUTE - (EXTRACT(MINUTE FROM MINUTE)::INTEGER % 30 || 'minutes')::INTERVAL, 'hh24:mi') ||
#         ' – ' ||
#         to_char(MINUTE - (EXTRACT(MINUTE FROM MINUTE)::INTEGER % 30 || 'minutes')::INTERVAL + '29 minutes'::INTERVAL, 'hh24:mi')
#             AS half_hour,
#         to_char(MINUTE - (EXTRACT(MINUTE FROM MINUTE)::INTEGER % 15 || 'minutes')::INTERVAL, 'hh24:mi') ||
#         ' – ' ||
#         to_char(MINUTE - (EXTRACT(MINUTE FROM MINUTE)::INTEGER % 15 || 'minutes')::INTERVAL + '14 minutes'::INTERVAL, 'hh24:mi')
#             AS quarter_hour,
#         -- Minute (0 - 59)
#         EXTRACT(MINUTE FROM MINUTE) AS minute
#     FROM (SELECT '0:00'::TIME + (SEQUENCE.MINUTE || ' minutes')::INTERVAL AS MINUTE
#         FROM generate_series(0,1439) AS SEQUENCE(MINUTE)
#         GROUP BY SEQUENCE.MINUTE
#         ) DQ
#     ORDER BY 1
#     """
# )

# QUERY LISTS

create_table_queries = [
    create_dim_date,
    create_dim_location,
    create_dim_time,
    create_fact_count,
    create_fact_weather,
    create_staging_weather,
    create_staging_NonMotCount,
    create_staging_NonMotLocation
]

drop_table_queries = [
    drop_dim_date,
    drop_dim_location,
    drop_dim_time,
    drop_fact_count,
    drop_fact_weather,
    drop_staging_NonMotCount,
    drop_staging_NonMotLocation,
    drop_staging_weather
]

copy_table_queries = [
    copy_staging_NonMotCount,
    copy_staging_NonMotLocation,
    copy_staging_weather,
    copy_dim_time,
    copy_dim_date,
]

insert_table_queries = [
    insert_dim_location,
    insert_fact_count,
    insert_fact_weather,
]

drop_staging_queries = [
    drop_staging_NonMotCount,
    drop_staging_NonMotLocation,
    drop_staging_weather,
]
