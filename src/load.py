import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from os import getenv
from sqlalchemy import create_engine, text, TIMESTAMP

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')
DB_USER = getenv("DB_USER")
DB_PASSWORD = getenv("DB_PASSWORD")
DB_HOST = getenv("DB_HOST")
DB_PORT = getenv("DB_PORT")
DB_NAME = getenv("DB_NAME")


# 1. Connect to PostgreSQL
db_url = getenv("DB_URL")


engine = create_engine(db_url)

# Read the fully transformed CSVs
dim_teams_df = pd.read_csv("data/processed/dim_teams.csv")
fact_matches_df = pd.read_csv("data/processed/fact_matches.csv", parse_dates=['match_date'])

#1. UPSERT DIMENSION TABLE
print("loading dim_teams...")
dim_teams_df.to_sql(
    'stg_dim_teams',
    engine,
    schema='sports_data_engine',
    if_exists='replace',
    index=False
)

#2. UPSERT FACT TABLE
print("Loading fact_matches...")
fact_matches_df.to_sql(
    'stg_fact_matches',
    engine,
    schema='sports_data_engine',
    if_exists='replace',
    index=False,
    dtype={
        "match_date": TIMESTAMP()
    }
)

print("Staging tables created successfully.")

# 3. UPSERT SQL

upsert_teams = text('''
    INSERT INTO sports_data_engine.dim_teams (team_id, team_name)
    SELECT team_id, team_name
    FROM sports_data_engine.stg_dim_teams
    ON CONFLICT (team_id) DO NOTHING;
''')


# EXCLUDED refers to the new incoming data that conflicted with the existing row
upsert_matches = text('''
    INSERT INTO sports_data_engine.fact_matches
        (match_id, home_team_id, away_team_id, home_score, away_score, status, match_date)
    SELECT match_id, home_team_id, away_team_id, home_score, away_score, status, match_date
    FROM sports_data_engine.stg_fact_matches
    ON CONFLICT (match_id)
    DO UPDATE SET
     home_score = EXCLUDED.home_score,
     away_score = EXCLUDED.away_score,
     status = EXCLUDED.status;
''')

#4 Excute the SQL and clean up
# Transcation
print("Starting database transaction...")

try: 
    with engine.begin() as conn: 
        # Load/update dimension table 
        print("Updating dim_teams...") 
        conn.execute(upsert_teams) 
        # Load/update fact table 
        print("Updating fact_matches...") 
        conn.execute(upsert_matches) 
        # Remove staging tables after successful load 
        print("Removing staging tables...") 

        conn.execute( text(""" DROP TABLE sports_data_engine.stg_dim_teams; """) ) 
        conn.execute( text(""" DROP TABLE sports_data_engine.stg_fact_matches; """) ) 
        # If we reach here, engine.begin() committed successfully. 
        print("Transaction committed successfully.") 
        print("Incremental load completed successfully.") 

except Exception as e: 
    # engine.begin() automatically rolls back 
    # # the transaction if an exception occurs. 
    
    print("Database load failed.") 
    print(f"Error: {e}") 
    raise













