# Sports Data Engine: Automated ETL Pipeline

An end-to-end, containerized ETL data pipeline that extracts Premier League match data from an external API, transforms the raw JSON into a relational Star Schema, and performs incremental loads (Upserts) into a PostgreSQL Data Warehouse. 

## 🏗️ Architecture & Data Flow

1. **Extract (`src/extract.py`)**: Fetches raw JSON match data from the `football-data.org` REST API.
2. **Transform (`src/transform.py`)**: Utilizes Pandas to flatten nested JSON, enforce strict data typing, and split the data into a Star Schema.
3. **Load (`src/load.py`)**: Connects to PostgreSQL via SQLAlchemy and executes SQL `ON CONFLICT` statements to upsert data, handling both new match inserts and status updates for existing matches.
4. **Serve (`src/report.py`)**: Executes complex `JOIN` queries across the role-playing dimensions to generate human-readable analytical reports.
5. **Orchestrate (`pipeline.py`)**: A master execution script that triggers the pipeline sequentially, designed to be scheduled via OS cron jobs or visual automation nodes like n8n.

## 🛠️ Tech Stack
* **Language:** Python 3 (Pandas, SQLAlchemy, Requests)
* **Database:** PostgreSQL 15
* **Infrastructure:** Docker & Docker Compose
* **Orchestration:** Native Python subprocess (compatible with n8n/cron)

## 🚀 Key Engineering Features

* **Dimensional Data Modeling:** Implements a strict Star Schema architecture. Text-heavy attributes are isolated in a `dim_teams` table, while the `fact_matches` table stores highly optimized numeric metrics (scores) and Foreign Keys.
* **Incremental Loading (Upserts):** Pipeline handles daily, automated runs without causing primary key conflicts. It intelligently ignores duplicate dimension records and updates fact records as future matches transition to `FINISHED`.
* **Containerized Environment:** The database infrastructure is fully decoupled from the host machine using Docker Compose, guaranteeing identical setups across different deployment environments.
* **Role-Playing Dimensions:** Demonstrates advanced SQL querying by joining the `dim_teams` table to the fact table twice (as both Home Team and Away Team) to reconstruct the event context.

## ⚙️ Local Setup & Execution

### Prerequisites
* Python 3.10+
* Docker Desktop installed and running
* API Key from [football-data.org](https://www.football-data.org/) (Optional: Currently configured for free-tier open endpoints)

### 1. Spin up the Data Warehouse
* Start the isolated PostgreSQL container:
```bash
docker compose up -d
````
### 2. Apply the Database Schema
* Execute the DDL script to create the schemas and tables:

```bash
docker exec -i sports_data_engine-postgres-1 psql -U admin -d epl_analytics < sql/01_schema.sql
````

### 3. Setup Python Environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
pip install pandas sqlalchemy psycopg2-binary requests
```

### 4. Run the Pipeline
* Execute the master orchestration script to trigger the Extract, Transform, Load, and Reporting phases:

```bash
python pipeline.py
```

