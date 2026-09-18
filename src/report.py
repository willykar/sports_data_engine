import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pathlib import Path
from os import getenv

BASE_DIR = Path(__file__).resolve().parent.parent

QUERY = """
SELECT
    f.match_date::date AS match_day,
    home.team_name AS home_team,
    f.home_score,
    f.away_score,
    away.team_name AS away_team,
    f.status
FROM sports_data_engine.fact_matches AS f
JOIN sports_data_engine.dim_teams AS home
    ON f.home_team_id = home.team_id
JOIN sports_data_engine.dim_teams AS away
    ON f.away_team_id = away.team_id
ORDER BY f.match_date DESC
LIMIT 10;
"""


def main():
    load_dotenv(BASE_DIR / ".env")

    db_url = getenv("DB_URL")

    if not db_url:
        raise ValueError("DB_URL is not set")

    engine = create_engine(db_url)

    print("Executing query against PostgreSQL...")
    df_report = pd.read_sql_query(QUERY, engine)

    print("\n--- LATEST 10 MATCHES ---")
    print(df_report.to_string(index=False))

    reports_dir = BASE_DIR / "data" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    report_path = reports_dir / "latest_matches_report.csv"
    df_report.to_csv(report_path, index=False)

    print(f"\nSuccess! Human-readable report saved to: {report_path}")


if __name__ == "__main__":
    main()
