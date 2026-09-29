"""
Local development runner.

Runs the same stages as the Airflow DAG (dags/sports_data_engine_dag.py), in
the same order, without needing the Airflow stack — useful for exercising the
pipeline from a plain virtualenv.

The DAG is the authoritative orchestrator. Keep the stage order here in step
with it.
"""

import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.extract import main as run_extract
from src.transform import main as run_transform
from src.load import main as run_load
from src.report import main as run_report

STAGES = [
    ("Extracting data from the API", run_extract),
    ("Transforming raw JSON and validating", run_transform),
    ("Loading into PostgreSQL", run_load),
    ("Generating the report", run_report),
]


def main():
    print("Starting daily EPL data pipeline...")

    print("Step 0: running the automated test suite...")
    subprocess.run([sys.executable, "-m", "pytest"], cwd=BASE_DIR, check=True)
    print("All automated tests passed.")

    for number, (description, run_stage) in enumerate(STAGES, start=1):
        print(f"Step {number}: {description}...")
        run_stage()

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError:
        print("Pipeline failed: the test suite did not pass.")
        sys.exit(1)
    except Exception as error:
        print(f"Pipeline failed: {error}")
        sys.exit(1)
