"""
Local development runner.

Supports running both the PostgreSQL (ETL) pipeline and the Snowflake + dbt (ELT)
pipeline without needing the Airflow stack — useful for exercising the pipeline
from a plain virtualenv.
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.extract import main as run_extract
from src.transform import main as run_transform
from src.load import main as run_load
from src.report import main as run_report
from src.load_raw_snowflake import main as run_load_snowflake
from src.run_dbt import run_dbt

POSTGRES_STAGES = [
    ("Extracting data from the API", run_extract),
    ("Transforming raw JSON and validating", run_transform),
    ("Loading into PostgreSQL", run_load),
    ("Generating the report", run_report),
]

SNOWFLAKE_STAGES = [
    ("Extracting data from the API", run_extract),
    ("Landing raw JSON payload into Snowflake (ELT)", run_load_snowflake),
    ("Executing dbt transformations & tests", lambda: run_dbt("build")),
]


def run_pipeline(target="postgres"):
    print(f"Starting daily EPL data pipeline (target: {target})...")

    print("Step 0: running the automated test suite...")
    subprocess.run([sys.executable, "-m", "pytest"], cwd=BASE_DIR, check=True)
    print("All automated tests passed.")

    stages_to_run = []
    if target in ("postgres", "all"):
        stages_to_run.extend(POSTGRES_STAGES)
    if target in ("snowflake", "all"):
        stages_to_run.extend(SNOWFLAKE_STAGES)

    for number, (description, run_stage) in enumerate(stages_to_run, start=1):
        print(f"Step {number}: {description}...")
        run_stage()

    print(f"Pipeline completed successfully for target '{target}'.")


def main():
    parser = argparse.ArgumentParser(description="Run EPL data pipeline")
    parser.add_argument(
        "--target",
        choices=["postgres", "snowflake", "all"],
        default="postgres",
        help="Warehouse target (default: postgres)",
    )
    args = parser.parse_args()
    run_pipeline(target=args.target)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        print("Pipeline failed: the test suite or dbt build did not pass.")
        sys.exit(1)
    except Exception as error:
        print(f"Pipeline failed: {error}")
        sys.exit(1)
