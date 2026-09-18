# Sports Data Engine — Automated ETL Pipeline

An end-to-end ETL pipeline that extracts Premier League match data from the
[football-data.org](https://www.football-data.org/) API, transforms the nested
JSON into a star schema with Pandas, validates it, and loads it incrementally
into PostgreSQL through staging tables and transactional SQL upserts.

Re-running the pipeline is safe: new matches are inserted, existing matches
have their scores and statuses updated, and nothing is duplicated.

---

## Architecture

```text
football-data.org API
        │
        ▼
  src/extract.py        raw JSON  →  data/raw/season_2025_2026.json
        │
        ▼
  src/transform.py      flatten → star schema → validate → CSV
        │                         data/processed/dim_teams.csv
        │                         data/processed/fact_matches.csv
        ▼
  src/load.py           CSV → staging tables → UPSERT → production
        │                     (all inside one transaction)
        ▼
   PostgreSQL
```

`pipeline.py` orchestrates the three stages with `subprocess`, and **runs the
full test suite first** — if any test fails the pipeline stops before touching
the API or the database. Any stage returning a non-zero exit code aborts the
run.

`src/report.py` is a standalone reporting script. It is **not** part of the
automated pipeline run; invoke it directly when you want a report.

---

## Repository layout

```text
pipeline.py               orchestrator: test gate → extract → transform → load
src/
  extract.py              football-data.org API → raw JSON
  transform.py            flatten, build star schema, validate, write CSVs
  load.py                 staging load + transactional UPSERT
  report.py               standalone analytical report (run manually)
  setup_db.py             applies sql/01_schema.sql to the configured database
sql/
  01_schema.sql           schema + dim_teams + fact_matches DDL
  02_queries.sql          example analytical queries
tests/
  test_transform.py       12 tests
  test_validation.py      16 tests
  test_load.py             5 tests
docker-compose.yml        local PostgreSQL 15
data/raw/ processed/ reports/    pipeline output (gitignored)
```

---

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
| Data | Pandas 2.3 |
| Database access | SQLAlchemy 2.0, psycopg2 |
| HTTP | Requests |
| Database | PostgreSQL 15 |
| Local infrastructure | Docker Compose |
| Hosted database | Supabase PostgreSQL |
| Testing | pytest |
| Config | python-dotenv |

---

## Setup

### Prerequisites

- Python 3.10+
- Docker Desktop (for the local database), or a Supabase project
- A free [football-data.org](https://www.football-data.org/) API token —
  **required**; the extractor sends it as an `X-Auth-Token` header

### 1. Configure environment variables

Create a `.env` file in the project root. It supplies both the application's
connection and the local container's credentials, so it must exist before you
start Docker.

```bash
# Application -> database
DB_URL=postgresql+psycopg2://admin:your_password@localhost:5432/epl_analytics

# football-data.org API token
football_data_api_key=your_football_data_org_token

# Credentials the local Docker container is created with
DB_USER=admin
DB_PASSWORD=your_password
DB_NAME=epl_analytics
```

`DB_URL` is the only variable the application reads, and it can point at
either the local Docker database or a Supabase connection string. The three
`DB_*` values below it are consumed by `docker-compose.yml` when it builds the
local container — keep them consistent with `DB_URL` when running locally.

`.env` is gitignored. Never commit it.

### 2. Start the local database

```bash
docker compose up -d
```

PostgreSQL 15 on port 5432, created with the `DB_USER`, `DB_PASSWORD` and
`DB_NAME` from `.env`. Compose fails with an explicit message if any of them
is missing, rather than starting a half-configured container.

Skip this step if you are using Supabase — just point `DB_URL` at it.

### 3. Set up the Python environment

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

On macOS or Linux, use `source venv/bin/activate`.

### 4. Create the schema

```bash
python src/setup_db.py
```

This applies `sql/01_schema.sql` through SQLAlchemy and works against local
PostgreSQL and Supabase alike. Against the local container you can instead
pipe the DDL in directly:

```bash
docker exec -i sports_data_engine-postgres-1 psql -U admin -d epl_analytics < sql/01_schema.sql
```

### 5. Run the pipeline

```bash
python pipeline.py
```

Tests run first, then extract, transform and load. Run it from the project
root — the extractor writes its raw JSON relative to the working directory.

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
database.

---

## Reporting

```bash
python src/report.py
```

Joins `fact_matches` against `dim_teams` twice — once per role — prints the
result and writes `data/reports/latest_matches_report.csv`. Requires a
populated database.
