import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from pathlib import Path
from os import getenv

# 1. setup paths and database connection
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")
DB_NAME = getenv("DB_NAME")

# 1. Connect to PostgreSQL
db_url = getenv("DB_URL")

engine = create_engine(db_url)

#2 Write the SQL Query as a multi-line string
query = """
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
JOIN sports_data_engine.dim_teams away
    ON f.away_team_id = away.team_id
ORDER BY f.match_date ASC
LIMIT 10;
"""


#3. Excute the query and load results into pandas
print("Excute query againt postgreSQL...")
df_report = pd.read_sql_query(query, engine)

#4. Display the results in the terminal
print("\n--- LATEST 10 MATCHES ---")
print(df_report.to_string(index=False))

#5. save the report to disk
REPORTS_DIR = BASE_DIR / 'data' / 'reports'
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

report_path = REPORTS_DIR / 'latest_matches_report.csv'
df_report.to_csv(report_path, index=False)

print(f"\nSuccess! Human-readable report saved to: {report_path}")
