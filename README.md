# Sports Data Engine — Automated ETL Pipeline

An end-to-end ETL pipeline that extracts Premier League match data from the
[football-data.org](https://www.football-data.org/) API, transforms the nested
JSON into a star schema with Pandas, validates it, and loads it incrementally
into Supabase PostgreSQL through staging tables and transactional SQL upserts.

Orchestrated by Apache Airflow running on Docker Compose. Re-running is safe:
new matches are inserted, existing matches have their scores and statuses
updated, and nothing is duplicated.

---

## Architecture

```text
                    Airflow DAG (daily)
                            |
                            v
                   run_test_safety_gate     pytest must pass before
                            |               anything touches the API
                            v
                     extract_matches        football-data.org API
                            |               -> data/raw/season_2025_2026.json
                            v
                 transform_and_validate     flatten -> star schema -> validate
                            |               -> data/processed/*.csv
                            v
                    load_to_supabase        CSV -> staging -> UPSERT
                            |               (one transaction)
                            v
                     generate_report        analytical SQL -> data/reports/
                            |
                            v
                   Supabase PostgreSQL
```

Each stage is an Airflow task calling the matching module's `main()`. The
modules import cleanly, so they run unchanged inside a task, from
`pipeline.py`, or directly as scripts.

## Repository layout

```text
dags/
  sports_data_engine_dag.py   the Airflow DAG: the authoritative orchestrator
Dockerfile                    apache/airflow:3.1.8 + this project's deps
docker-compose.yaml           Airflow stack (CeleryExecutor, Redis, metadata DB)
pipeline.py                   local runner: the same stages without Airflow
src/
  extract.py                  football-data.org API -> raw JSON
  transform.py                flatten, build star schema, validate, write CSVs
  load.py                     staging load + transactional UPSERT
  report.py                   analytical report (standalone)
  setup_db.py                 applies sql/01_schema.sql to the database
sql/
  01_schema.sql               schema + dim_teams + fact_matches DDL
  02_queries.sql              example analytical queries
tests/
  test_transform.py           12 tests
  test_validation.py          16 tests
  test_load.py                 5 tests
data/raw/ processed/ reports/ pipeline output (gitignored)
```

## Data model

A star schema in the `sports_data_engine` schema.

**`dim_teams`**

| Column | Type | Notes |
|---|---|---|
| `team_id` | `INTEGER` | primary key |
| `team_name` | `TEXT` | not null, unique |

**`fact_matches`**

| Column | Type | Notes |
|---|---|---|
| `match_id` | `INTEGER` | primary key |
| `home_team_id` | `INTEGER` | not null → `dim_teams.team_id` |
| `away_team_id` | `INTEGER` | not null → `dim_teams.team_id` |
| `home_score` | `INTEGER` | nullable — see below |
| `away_score` | `INTEGER` | nullable — see below |
| `status` | `TEXT` | not null |
| `match_date` | `TIMESTAMP` | not null |

`dim_teams` is a **role-playing dimension**: `fact_matches` joins it twice, as
home team and as away team, to reconstruct the full match.

**A missing score is `NULL`, never `0`.** An unplayed match carries `NaN`
through the transform and `NULL` into the database, because `0–0` is a real
football result and must stay distinguishable from "not played yet". A test
protects this.

---

## Engineering features

- **Incremental loading.** `dim_teams` upserts with `ON CONFLICT DO NOTHING`;
  `fact_matches` upserts with `ON CONFLICT DO UPDATE`, refreshing score and
  status as matches progress. Repeated runs never duplicate rows.
- **Staging tables.** Transformed CSVs land in `stg_dim_teams` and
  `stg_fact_matches` (recreated each run), and production tables are only
  touched by controlled SQL upserts reading from staging. The staging tables
  are dropped at the end of the transaction.
- **Transactional loading.** Staging counts, both upserts and the staging
  cleanup run inside a single `engine.begin()` block. Any failure rolls the
  whole thing back — covered by a dedicated rollback test.
- **Data quality gate.** `validate_data()` runs before anything is written:
  missing and duplicate keys, empty team names, `match_date` dtype,
  referential integrity of both team foreign keys, teams playing themselves,
  negative scores, and status values outside the permitted set (`SCHEDULED`,
  `TIMED`, `IN_PLAY`, `PAUSED`, `FINISHED`, `POSTPONED`, `SUSPENDED`,
  `CANCELLED`). A violation raises and stops the run.
- **Test safety gate.** `pipeline.py` runs `pytest` before the ETL stages.
- **Portable database target.** The application only ever reads `DB_URL`, so
  the same code and schema run against local Docker PostgreSQL or hosted
  Supabase with no change.

---

## Tech stack

| | |
|---|---|
| Language | Python 3.10+ |
| Orchestration | Apache Airflow 3.1.8 (CeleryExecutor + Redis) |
| Containers | Docker Compose |
| Data | Pandas 2.3 |
| Database access | SQLAlchemy 2.0, psycopg2 |
| HTTP | Requests |
| Database | Supabase PostgreSQL |
| Testing | pytest |
| Config | python-dotenv |

---

## Setup

### Prerequisites

- Docker Desktop (for the Airflow stack)
- Python 3.10+ (only if running without Airflow)
- A Supabase project
- A free [football-data.org](https://www.football-data.org/) API token —
  **required**; the extractor sends it as an `X-Auth-Token` header

### 1. Configure environment variables

Create a `.env` file in the project root:

```bash
DB_URL=postgresql+psycopg2://<user>:<password>@<host>:5432/postgres
football_data_api_key=your_football_data_org_token
```

`DB_URL` is the only database variable the application reads — point it at
your Supabase connection string. `.env` is gitignored and is mounted into the
Airflow containers at `/opt/airflow/.env`; never commit it.

### 2. Create the schema

```bash
python src/setup_db.py
```

Applies `sql/01_schema.sql` through SQLAlchemy. Run once per database.

### 3a. Run with Airflow

```bash
docker compose up -d --build
```

Airflow's UI is at `http://localhost:8080` (default credentials
`airflow` / `airflow`). Enable and trigger `sports_data_engine_pipeline`.

The compose file mounts `dags/`, `src/`, `tests/`, `data/`, `config/`,
`plugins/` and `.env` into the containers, so code changes apply without a
rebuild. Rebuild only when `requirements.txt` changes:

```bash
docker compose build --no-cache
```

### 3b. Run without Airflow

```bash
python -m venv venv && venv\Scripts\activate && pip install -r requirements.txt
```

```bash
python pipeline.py
```

Runs the test suite, then the same four stages in the same order. On macOS or
Linux use `source venv/bin/activate`.

---

## Tests

```bash
pytest -v
```

33 tests, all passing:

| Suite | Tests | Covers |
|---|---|---|
| `test_transform.py` | 12 | flattening, `build_dim_teams()`, `build_fact_matches()` |
| `test_validation.py` | 16 | every data quality rule, including missing-score semantics |
| `test_load.py` | 5 | staging writes, both upsert statements, transaction orchestration, rollback on failure |

The load tests use mocked database objects, so the suite runs without a live
database. The DAG runs this same suite as its first task, so a failing test
stops the pipeline before it reaches the API.

---

## Reporting

```bash
python src/report.py
```

Joins `fact_matches` against `dim_teams` twice — once per role — prints the
result and writes `data/reports/latest_matches_report.csv`. Also runs as the
DAG's final task.
