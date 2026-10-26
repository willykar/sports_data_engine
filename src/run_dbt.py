"""
Executes dbt commands for the sports_data_engine project.

Orchestrates Snowflake model transformations and data quality tests
from both the local runner (pipeline.py) and Airflow DAGs.
"""

import subprocess
import sys
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DBT_DIR = BASE_DIR / "dbt"

load_dotenv(BASE_DIR / ".env")


def get_dbt_executable():
    """
    Locates the dbt executable within the active Python environment.
    """
    python_path = Path(sys.executable)
    dbt_exe = python_path.parent / ("dbt.exe" if sys.platform == "win32" else "dbt")

    if not dbt_exe.exists():
        # Fallback to sys.executable -m dbt
        return [sys.executable, "-m", "dbt.cli.main"]

    return [str(dbt_exe)]


def run_dbt(command="build", extra_args=None):
    """
    Runs a dbt command (e.g., 'run', 'test', 'build') targeting Snowflake.
    """
    cmd = get_dbt_executable() + [
        command,
        "--project-dir",
        str(DBT_DIR),
        "--profiles-dir",
        str(DBT_DIR),
    ]

    if extra_args:
        cmd.extend(extra_args)

    print(f"Running dbt command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=BASE_DIR, check=True)
    return result.returncode


def main():
    run_dbt("build")


if __name__ == "__main__":
    main()
