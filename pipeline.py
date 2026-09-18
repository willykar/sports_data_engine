import subprocess
import sys

print("Starting Daily EPL Data Pipeline...")

try:
    print("Running automated tests")
    subprocess.run([sys.executable, "-m", "pytest"],check=True)
    print("All automated tests passed.")

    print("Step 1: Extracting data from API...")
    subprocess.run([sys.executable, "src/extract.py"], check=True)

    print("Step 2: Transforming raw JSON to structured CSVs...")
    subprocess.run([sys.executable, "src/transform.py"], check=True)

    print("Step 3: Loading CSVs into PostgreSQL...")
    subprocess.run([sys.executable, "src/load.py"], check=True)

    # print("Step 4: Generating daily business reports...")
    # subprocess.run([sys.executable, "src/report.py"], check=True)

    print("Pipeline completed successfully!")

except subprocess.CalledProcessError as e:
    print(f"Pipeline failed at step: {e.cmd}")
    sys.exit(1)