# Sports Data Engine — Automated ETL & Snowflake ELT Pipeline

An end-to-end data pipeline that extracts Premier League match data from the
[football-data.org](https://www.football-data.org/) API. The project supports two
production architectures:

1. **Transactional PostgreSQL ETL:** Raw JSON $\rightarrow$ Pandas star-schema modeling and data quality validation $\rightarrow$ staging tables and transactional SQL upserts into PostgreSQL / Supabase.
2. **Cloud Warehouse Snowflake ELT:** Raw API JSON landed directly into Snowflake as semi-structured `VARIANT` payloads $\rightarrow$ modular in-warehouse modeling and automated testing with **dbt**.

Orchestrated by Apache Airflow running on Docker Compose (with local CLI execution via `pipeline.py`). Re-running is safe and idempotent across both warehouses.

---

## Architecture

```text
                                Airflow DAG / pipeline.py
                                           |
                                           v
                                 run_test_safety_gate
                             (pytest gate: 54 unit tests)
                                           |
                                           v
                                    extract_matches
                                 football-data.org API
                            -> data/raw/season_2025_2026.json
                                     /           \
                                    /             \
                  [PostgreSQL ETL Path]         [Snowflake ELT Path]
                           |                             |
                           v                             v
                transform_and_validate          load_to_snowflake
               Pandas flatten & validate       Raw JSON -> RAW.RAW_MATCHES
                           |                   (VARIANT column, MERGE upsert)
                           v                             |
                   load_to_supabase                      v
               CSV -> staging -> UPSERT        transform_and_test_dbt
               (in-transaction merge)          dbt build (models & 17 tests)
                           |                             |
                           v                             v
                    generate_report             Snowflake Data Cloud
               analytical SQL -> reports       (stg_matches, dim_teams,
                           |                    fact_matches)
                           v                             |
                  Supabase PostgreSQL                    |
                           \                             /
                            \                           /
                             v                         v
                                    pipeline_complete
```

---

## Repository layout

```text
dags/
  sports_data_engine_dag.py   Airflow DAG: orchestrates PostgreSQL and Snowflake paths
dbt/
  dbt_project.yml             dbt project configuration
  profiles.yml                Snowflake connection profile (reads from .env)
  models/
    staging/
      _sources.yml            Raw source declaration on RAW.RAW_MATCHES
      stg_matches.sql         Flattens VARIANT JSON; null score preservation
    marts/
      _schema.yml             Schema & integrity tests for dimensional models
      dim_teams.sql           Unique clubs dimension table
      fact_matches.sql        Match events fact table
  tests/                      Singular domain data quality tests
Dockerfile                    apache/airflow:3.1.8 + project dependencies
docker-compose.yaml           Airflow stack with mounted volumes (src, dags, dbt, tests)
pipeline.py                   Local runner supporting --target postgres|snowflake|all
src/
  extract.py                  API extraction (full competition or date-windowed)
  transform.py                Pandas flattening, star schema construction, validation
  load.py                     PostgreSQL staging load + transactional UPSERT
  load_raw_snowflake.py       Snowflake raw VARIANT landing with transactional MERGE
  run_dbt.py                  Programmatic runner for dbt build/test commands
  report.py                   Analytical SQL report against PostgreSQL
  setup_db.py                 Applies sql/01_schema.sql to PostgreSQL
sql/
  01_schema.sql               PostgreSQL schema + DDL
  02_queries.sql              Analytical queries
  03_snowflake_setup.sql      Snowflake database, warehouse, schemas and landing table DDL
tests/
  test_extract.py             11 extraction tests (windowing, error handling)
  test_transform.py           13 transformation tests (flattening, types, empty windows)
  test_validation.py          16 data quality and validation tests
  test_load.py                 5 PostgreSQL load and rollback tests
  test_load_snowflake.py       6 Snowflake raw loader tests (staging, MERGE, rollback)
  test_run_dbt.py              3 dbt runner orchestration tests
data/raw/ processed/ reports/ pipeline output artifacts (gitignored)
```

---

## Data model

The dimensional star schema is modeled identically across both warehouses:

**`dim_teams`**

| Column | Type | Notes |
|---|---|---|
| `team_id` | `INTEGER` / `NUMBER` | Primary key |
| `team_name` | `TEXT` / `VARCHAR` | Not null, unique |

**`fact_matches`**

| Column | Type | Notes |
|---|---|---|
| `match_id` | `INTEGER` / `NUMBER` | Primary key |
| `home_team_id` | `INTEGER` / `NUMBER` | Not null $\rightarrow$ `dim_teams.team_id` |
| `away_team_id` | `INTEGER` / `NUMBER` | Not null $\rightarrow$ `dim_teams.team_id` |
| `home_score` | `INTEGER` / `NUMBER` | Nullable — see below |
| `away_score` | `INTEGER` / `NUMBER` | Nullable — see below |
| `status` | `TEXT` / `VARCHAR` | Not null (`FINISHED`, `SCHEDULED`, `TIMED`, etc.) |
| `match_date` | `TIMESTAMP` | Kickoff datetime (UTC) |

`dim_teams` is a **role-playing dimension**: `fact_matches` joins it twice (as home team and away team) to reconstruct the full match fixture.

**A missing score is `NULL`, never `0`.** An unplayed or upcoming match carries `NaN`/`NULL` through both transformation paths. `0–0` is a genuine football result and must remain distinguishable from unplayed fixtures. Both `pytest` and `dbt` singular tests enforce this invariant.

---

## Engineering features

- **Dual Warehouse Architecture:** PostgreSQL for operational relational loading (ETL); Snowflake + dbt for modern cloud analytical warehousing (ELT).
- **Semi-Structured VARIANT Landing:** In Snowflake, raw JSON payloads land unadulterated into `RAW.RAW_MATCHES` (`payload VARIANT`), decoupling ingestion from transformation.
- **Atomic Upserts & Idempotency:**
  - PostgreSQL: Session staging table $\rightarrow$ `INSERT ... ON CONFLICT DO UPDATE`.
  - Snowflake: Temporary staging table $\rightarrow$ `MERGE INTO ... WHEN MATCHED THEN UPDATE ... WHEN NOT MATCHED THEN INSERT`.
- **dbt Modeling & In-Warehouse Testing:** 20 data models and tests compiling and running directly on Snowflake compute.
- **Safety Gate:** Automated test gate halts pipeline execution before any API calls or database mutations occur if unit tests fail.

---

## Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.10+ |
| Orchestration | Apache Airflow 3.1.8 (Docker Compose) |
| Cloud Warehouse | Snowflake |
| Transformation Framework | dbt Core 1.13 + dbt-snowflake |
| Relational Database | Supabase PostgreSQL / Local PostgreSQL |
| Data Processing | Pandas 2.3 |
| Connectors | snowflake-connector-python, SQLAlchemy 2.0, psycopg2 |
| Testing | pytest 9.1, dbt data tests |

---

## Setup & Execution

### 1. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:

```bash
# API Key
football_data_api_key=your_api_key

# PostgreSQL (Supabase / Local)
DB_URL=postgresql+psycopg2://user:password@host:5432/dbname

# Snowflake
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ROLE=ACCOUNTADMIN
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SPORTS_DATA
SNOWFLAKE_SCHEMA=RAW
```

### 2. Initialize Warehouses
- **PostgreSQL:** `python src/setup_db.py`
- **Snowflake:** Run `sql/03_snowflake_setup.sql` in your Snowflake worksheet to create database, warehouse, schemas, and landing table.

### 3. Run Pipeline Locally

```bash
# Run Snowflake ELT pipeline (extract -> raw landing -> dbt build)
python pipeline.py --target snowflake

# Run PostgreSQL ETL pipeline (extract -> transform -> load -> report)
python pipeline.py --target postgres

# Run both targets in a single run
python pipeline.py --target all
```

### 4. Run with Airflow

```bash
docker compose up -d --build
```
Access the Airflow UI at `http://localhost:8080` (default credentials: `airflow`/`airflow`) and trigger `sports_data_engine_pipeline`.

---

## Tests

```bash
# Run the complete Python test suite (54 passed)
pytest -v

# Run dbt data quality tests against Snowflake
dbt test --project-dir dbt --profiles-dir dbt
```

| Suite | Tests | Covers |
|---|---|---|
| `test_extract.py` | 11 | API requests, incremental windowing, token validation |
| `test_transform.py` | 13 | JSON flattening, star schema builds, empty window handling |
| `test_validation.py` | 16 | Data quality rules, score constraints, status domain checks |
| `test_load.py` | 5 | PostgreSQL staging, upsert statements, transaction rollbacks |
| `test_load_snowflake.py` | 6 | Snowflake config, VARIANT staging, MERGE statements, rollbacks |
| `test_run_dbt.py` | 3 | dbt CLI executable discovery and invocation |
| **dbt tests** | 17 | Primary keys, foreign key relationships, accepted values, score invariants |
