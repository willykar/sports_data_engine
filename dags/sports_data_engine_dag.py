import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

from airflow.decorators import dag, task

# Resolve project root so `src` is importable. This stays at module level
# because the in-task imports below depend on it, and it is cheap.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# Nothing from `src` is imported here on purpose. Airflow re-parses every DAG
# file on a short interval, so a top-level import would pull in pandas,
# SQLAlchemy and psycopg2 on every parse. The imports live inside the tasks,
# where they run once per execution instead. Each src.main() loads .env
# itself, so the DAG does not need to.


@dag(
    dag_id="sports_data_engine_pipeline",
    default_args={
        "retries": 1,
        "retry_delay": timedelta(minutes=5),
    },
    description="End-to-end Premier League data ingestion to Supabase with automated testing",
    schedule="@daily",
    catchup=False,
    start_date=datetime(2026, 1, 1),
    tags=["sports_data"],
)
def sports_data_engine():

    @task
    def run_test_safety_gate():
        """
        Executes pytest as a pre-flight safety check.
        Stops the pipeline if any unit or validation test fails.
        """
        print("Executing automated test suite...")

        subprocess.run(
            [sys.executable, "-m", "pytest", "tests/"],
            cwd=BASE_DIR,
            check=True,
        )

        print("All tests passed. Proceeding with ETL.")

    @task
    def extract_matches():
        """
        Extracts raw Premier League match data and writes it to data/raw/.
        """
        from src.extract import main as run_extract

        print("Starting extraction from external football API...")
        run_extract()
        print("Extraction complete: raw JSON stored.")

    @task
    def transform_and_validate():
        """
        Flattens the JSON, constructs dim_teams and fact_matches, and enforces
        data quality validations before saving CSVs.
        """
        from src.transform import main as run_transform

        print("Starting transformation and data quality checks...")
        run_transform()
        print("Transform complete: clean CSV artifacts written.")

    @task
    def load_to_supabase():
        """
        Stages processed CSVs in Supabase PostgreSQL and performs
        transactional ON CONFLICT UPSERTs into the production tables.
        """
        from src.load import main as run_load

        print("Starting transactional load into Supabase PostgreSQL...")
        run_load()
        print("Load complete: tables successfully updated.")

    @task
    def generate_report():
        """
        Runs analytical SQL queries against Supabase and writes the summary report.
        """
        from src.report import main as run_report

        run_report()
        print("Reporting complete: CSV generated in data/reports/.")

    # Pipeline execution flow (linear dependency).
    test_gate = run_test_safety_gate()
    extract = extract_matches()
    transform = transform_and_validate()
    load = load_to_supabase()
    report = generate_report()

    test_gate >> extract >> transform >> load >> report


# Instantiate the DAG.
sports_data_engine()
