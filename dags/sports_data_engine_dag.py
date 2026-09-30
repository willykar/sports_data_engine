import sys
import subprocess
from pathlib import Path
from datetime import date, datetime, timedelta

from airflow.decorators import dag, task

# Resolve project root so `src` is importable. This stays at module level
# because the in-task imports below depend on it, and it is cheap.
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

# How far either side of the run date the fixture check looks. Wide enough to
# catch results that landed late and fixtures about to be played, narrow
# enough that a quiet midweek ends the run immediately.
WINDOW_DAYS_BACK = 1
WINDOW_DAYS_AHEAD = 1


def window_for(ds):
    """
    The date window a run works on, derived from its logical date.

    Both the fixture check and the extract call this, so the two cannot drift
    apart -- a branch that green-lights a day whose extract window is empty
    would push an empty payload through the rest of the pipeline. Keying off
    the logical date rather than today's date also makes a run reproducible:
    re-running it, or backfilling one, fetches the same window.
    """
    day = date.fromisoformat(ds)
    return (
        (day - timedelta(days=WINDOW_DAYS_BACK)).isoformat(),
        (day + timedelta(days=WINDOW_DAYS_AHEAD)).isoformat(),
    )


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

    @task.branch
    def check_if_games_exist(ds=None):
        """
        Cheap gate in front of the pipeline: ask the API whether there are any
        fixtures in this run's window. One windowed request, nothing written
        and nothing loaded. If the window is empty the run ends here instead
        of re-processing anything.
        """
        from src.extract import fetch_matches

        date_from, date_to = window_for(ds)

        matches = fetch_matches(date_from=date_from, date_to=date_to).get("matches", [])
        print(f"{len(matches)} fixture(s) between {date_from} and {date_to}.")

        if not matches:
            return "no_games"
        return "run_test_safety_gate"

    @task
    def no_games():
        """
        Terminates the run when the fixture window is empty.
        """
        print("No fixtures in the window. Skipping the pipeline.")

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
    def extract_matches(ds=None):
        """
        Extracts this run's window of Premier League matches into data/raw/.

        Incremental by design: the payload holds the handful of matches around
        the logical date, not the whole season. The load is an upsert keyed on
        match_id, so a narrow payload updates those rows and leaves every other
        match in the warehouse untouched.
        """
        from src.extract import main as run_extract

        date_from, date_to = window_for(ds)

        print(f"Starting extraction for {date_from} to {date_to}...")
        run_extract(date_from=date_from, date_to=date_to)
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

    @task(trigger_rule="none_failed_min_one_success")
    def pipeline_complete():
        """
        Single terminal task both branches converge on, so there is one place
        to check whether a run finished. It needs a non-default trigger rule:
        under the default all_success it would be skipped along with whichever
        branch was not taken.
        """
        print("Run finished.")

    gate = check_if_games_exist()
    skip = no_games()
    test_gate = run_test_safety_gate()
    extract = extract_matches()
    transform = transform_and_validate()
    load = load_to_supabase()
    report = generate_report()
    done = pipeline_complete()

    # The branch picks one path; both converge on pipeline_complete.
    gate >> [test_gate, skip]
    test_gate >> extract >> transform >> load >> report >> done
    skip >> done


# Instantiate the DAG.
sports_data_engine()
