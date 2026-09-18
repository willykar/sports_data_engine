import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from os import getenv
from sqlalchemy import create_engine, text, TIMESTAMP

BASE_DIR = Path(__file__).resolve().parent.parent

def load_staging_tables(dim_teams_df, fact_matches_df, engine):
    dim_teams_df.to_sql(
        "stg_dim_teams",
        engine,
        schema="sports_data_engine",
        if_exists="replace",
        index=False
    )

    fact_matches_df.to_sql(
        "stg_fact_matches",
        engine,
        schema="sports_data_engine",
        if_exists="replace",
        index=False,
        dtype={"match_date": TIMESTAMP()}
    )

def upsert_teams(conn):
    conn.execute(text("""
        INSERT INTO sports_data_engine.dim_teams (team_id, team_name)
        SELECT team_id, team_name
        FROM sports_data_engine.stg_dim_teams
        ON CONFLICT (team_id) DO NOTHING;
    """))

def load_to_database(engine):
    count_staging_teams = text("""
        SELECT COUNT(*)
        FROM sports_data_engine.stg_dim_teams;
    """)

    count_staging_matches = text("""
        SELECT COUNT(*)
        FROM sports_data_engine.stg_fact_matches;
    """)

    print("Starting database transaction...")

    with engine.begin() as conn:
        staging_teams = conn.execute(
            count_staging_teams
        ).scalar_one()

        staging_matches = conn.execute(
            count_staging_matches
        ).scalar_one()

        print(f"Teams received from CSV: {staging_teams}")
        print(f"Matches received from CSV: {staging_matches}")

        print("Updating dim_teams...")
        upsert_teams(conn)

        print("Updating fact_matches...")
        upsert_matches(conn)

        print("Removing staging tables...")
        conn.execute(
            text("""
                DROP TABLE sports_data_engine.stg_dim_teams;
            """)
        )

        conn.execute(
            text("""
                DROP TABLE sports_data_engine.stg_fact_matches;
            """)
        )

        print("Transaction committed successfully.")

        
def upsert_matches(conn):
    conn.execute(text("""
        INSERT INTO sports_data_engine.fact_matches
            (match_id, home_team_id, away_team_id,
             home_score, away_score, status, match_date)
        SELECT match_id, home_team_id, away_team_id,
               home_score, away_score, status, match_date
        FROM sports_data_engine.stg_fact_matches
        ON CONFLICT (match_id)
        DO UPDATE SET
            home_score = EXCLUDED.home_score,
            away_score = EXCLUDED.away_score,
            status = EXCLUDED.status;
    """))

def main():

    load_dotenv(BASE_DIR / '.env')

    # 1. Connect to PostgreSQL
    db_url = getenv("DB_URL")

    if not db_url:
        raise ValueError("DB_URL is not set")

    engine = create_engine(db_url)

    # Read the fully transformed CSVs
    dim_teams_df = pd.read_csv(BASE_DIR / "data" / "processed" / "dim_teams.csv")
    fact_matches_df = pd.read_csv(BASE_DIR / "data/processed/fact_matches.csv", parse_dates=['match_date'])

    #1. UPSERT DIMENSION TABLE
    print("loading dim_teams...")
    #2. UPSERT FACT TABLE
    print("Loading fact_matches...")
    load_staging_tables(
        dim_teams_df,
        fact_matches_df,
        engine
    )

    print("Staging tables created successfully.")

    try:
       load_to_database(engine)
       print("Incremental load completed successfully.")

    except Exception as e: 
        # engine.begin() automatically rolls back 
        # # the transaction if an exception occurs. 
        
        print("Database load failed.") 
        print(f"Error: {e}") 
        raise


if __name__ == "__main__":
    main()







