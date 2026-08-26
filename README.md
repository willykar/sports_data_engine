# Sports Data Engine: Automated ETL Pipeline

An end-to-end, containerized ETL data pipeline that extracts Premier League match data from an external API, transforms the raw JSON into a relational Star Schema, and performs incremental loads (Upserts) into a PostgreSQL Data Warehouse. 

## 🏗️ Architecture & Data Flow

1. **Extract (`src/extract.py`)**: Fetches raw JSON match data from the `football-data.org` REST API.
2. **Transform (`src/transform.py`)**: Utilizes Pandas to flatten nested JSON, normalize and validate data types, and split the data into a Star Schema.
3. **Load (`src/load.py`)**: Connects to PostgreSQL via SQLAlchemy and executes SQL `ON CONFLICT` statements to upsert data, handling both new match inserts and status updates for existing matches.
4. **Report (`src/report.py`)**: Executes complex `JOIN` queries across the role-playing dimensions to generate human-readable analytical reports.
5. **Orchestrate (`pipeline.py`)**: A master execution script that triggers the pipeline sequentially, designed to be scheduled via OS cron jobs or visual automation nodes like n8n.

## 🛠️ Tech Stack
**Language:** Python 3, Pandas, SQLAlchemy, Requests
- **Database:** PostgreSQL 15
- **Local Infrastructure:** Docker & Docker Compose
- **Cloud Database:** Supabase PostgreSQL
- **Orchestration:** Python subprocess pipeline; designed to be schedulable via cron or a workflow orchestrator.

## 🚀 Key Engineering Features

- **Dimensional Data Modeling:** Implements a Star Schema with a `dim_teams` dimension and `fact_matches` fact table containing foreign-key relationships and match metrics.
- **Incremental Loading (Upserts):** Handles repeated pipeline runs without creating duplicate records. Existing dimension records are ignored, while existing matches are updated as their scores and statuses change.
- **Data Quality Validation:** Validates required fields, duplicate IDs, datetime types, foreign-key relationships, invalid statuses, self-matches, and negative scores before data is loaded.
- **Staging Tables:** Loads transformed data into temporary staging tables before applying controlled SQL `UPSERT` operations to the production tables.
- **Transactional Loading:** Uses SQLAlchemy transactions so related database updates are committed together or rolled back if a database operation fails.
- **Role-Playing Dimensions:** Joins the `dim_teams` table twice as the Home Team and Away Team to reconstruct match context.
- **Cloud Database Integration:** Uses Supabase PostgreSQL as the hosted database environment while Docker Compose provides an isolated local PostgreSQL environment for development.

## ⚙️ Local Setup & Execution

### Prerequisites
* Python 3.10+
* Docker Desktop installed and running
* API Key from [football-data.org](https://www.football-data.org/) (Optional: Currently configured for free-tier open endpoints)
* A Supabase project for cloud PostgreSQL

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

### 3. Configure Environment Variables
* Create a .env file:
```bash
DB_URL=your_postgresql_connection_string
```
* For the cloud environment, this can be your Supabase PostgreSQL connection string.
* Do not commit .env to Git.

### 4. Setup Python Environment
```bash
python -m venv venv
venv\Scripts\activate  # On Windows
pip install -r requirements.txt
```

### 5. Run the Pipeline
* Execute the master orchestration script to trigger the Extract, Transform, Load, and Reporting phases:

```bash
python pipeline.py
```

### The pipeline will:

Extract
   ↓
Transform
   ↓
Validate
   ↓
Load
   ↓
Report

### ☁️ Supabase
* The pipeline can connect to Supabase PostgreSQL using the DB_URL environment variable.
* Supabase provides the hosted PostgreSQL database, while the application continues to use standard PostgreSQL and SQLAlchemy. The same schema and incremental loading logic can therefore be used against either the local Docker database or the hosted Supabase database.



