-- Snowflake Environment & Raw Storage Setup for sports_data_engine

-- 1. Database and Warehouse Setup
CREATE DATABASE IF NOT EXISTS SPORTS_DATA;
USE DATABASE SPORTS_DATA;

CREATE WAREHOUSE IF NOT EXISTS COMPUTE_WH
    WITH WAREHOUSE_SIZE = 'XSMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE;

-- 2. Schema Setup
-- RAW: Landing schema for raw API payloads
CREATE SCHEMA IF NOT EXISTS RAW;

-- ANALYTICS: Target schema for dbt dimensional models (dim_teams, fact_matches)
CREATE SCHEMA IF NOT EXISTS ANALYTICS;

-- 3. Raw Storage Table
-- Stores unmodified API match JSON in a VARIANT column for ELT processing.
-- Keyed on match_id to support idempotent upserts during ingestion.
CREATE TABLE IF NOT EXISTS RAW.RAW_MATCHES (
    match_id NUMBER PRIMARY KEY,
    payload VARIANT NOT NULL,
    loaded_at TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

COMMENT ON TABLE RAW.RAW_MATCHES IS 'Raw football-data.org match payloads stored as VARIANT for dbt modeling';
