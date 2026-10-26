"""
Loads raw football match JSON payloads into Snowflake.

Follows the ELT pattern: raw API data is landed directly into Snowflake
as semi-structured VARIANT data, preserving the complete source payload.
dbt then transforms and models the raw data downstream.
"""

import json
from os import getenv
from pathlib import Path
from dotenv import load_dotenv
import snowflake.connector

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_RAW_FILE = BASE_DIR / "data" / "raw" / "season_2025_2026.json"


def get_snowflake_config():
    """
    Read Snowflake credentials from environment variables.
    Never hardcode credentials in source code.
    """
    load_dotenv(BASE_DIR / ".env")

    account = getenv("SNOWFLAKE_ACCOUNT")
    user = getenv("SNOWFLAKE_USER")
    password = getenv("SNOWFLAKE_PASSWORD")

    if not all([account, user, password]):
        missing = [
            var for var, val in [
                ("SNOWFLAKE_ACCOUNT", account),
                ("SNOWFLAKE_USER", user),
                ("SNOWFLAKE_PASSWORD", password),
            ] if not val
        ]
        raise ValueError(f"Missing required Snowflake environment variable(s): {', '.join(missing)}")

    return {
        "account": account,
        "user": user,
        "password": password,
        "role": getenv("SNOWFLAKE_ROLE", "ACCOUNTADMIN"),
        "warehouse": getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        "database": getenv("SNOWFLAKE_DATABASE", "SPORTS_DATA"),
        "schema": getenv("SNOWFLAKE_SCHEMA", "RAW"),
    }


def get_snowflake_connection(config=None):
    """
    Establish a connection to Snowflake.
    """
    cfg = config or get_snowflake_config()
    return snowflake.connector.connect(
        account=cfg["account"],
        user=cfg["user"],
        password=cfg["password"],
        role=cfg.get("role"),
        warehouse=cfg.get("warehouse"),
        database=cfg.get("database"),
        schema=cfg.get("schema"),
    )


def load_raw_matches(conn, matches):
    """
    Load raw match payloads into Snowflake RAW.RAW_MATCHES.

    Uses a session-scoped temporary staging table and a single MERGE INTO
    statement to ensure idempotent, atomic upserts.

    Empty payloads (e.g. quiet mid-week incremental window) exit cleanly as a no-op.
    """
    if not matches:
        print("No matches in payload to load. Skipping Snowflake raw load.")
        return 0

    records = [
        (match["id"], json.dumps(match))
        for match in matches
        if "id" in match
    ]

    if not records:
        print("No valid match records with 'id' found in payload.")
        return 0

    cursor = conn.cursor()
    try:
        print(f"Staging {len(records)} raw match payload(s) into temporary table...")
        cursor.execute("""
            CREATE TEMPORARY TABLE IF NOT EXISTS stg_raw_matches (
                match_id NUMBER,
                payload_str VARCHAR
            );
        """)

        cursor.execute("TRUNCATE TABLE IF EXISTS stg_raw_matches;")

        cursor.executemany(
            "INSERT INTO stg_raw_matches (match_id, payload_str) VALUES (%s, %s);",
            records
        )

        print("Executing MERGE into RAW.RAW_MATCHES...")
        cursor.execute("""
            MERGE INTO RAW_MATCHES target
            USING (
                SELECT match_id, PARSE_JSON(payload_str) AS payload
                FROM stg_raw_matches
            ) source
            ON target.match_id = source.match_id
            WHEN MATCHED THEN UPDATE SET
                payload = source.payload,
                loaded_at = CURRENT_TIMESTAMP()
            WHEN NOT MATCHED THEN INSERT (match_id, payload, loaded_at)
            VALUES (source.match_id, source.payload, CURRENT_TIMESTAMP());
        """)

        cursor.execute("DROP TABLE IF EXISTS stg_raw_matches;")
        conn.commit()
        print(f"Successfully loaded and merged {len(records)} match(es) into Snowflake.")
        return len(records)

    except Exception as e:
        conn.rollback()
        print(f"Snowflake raw load failed: {e}")
        raise
    finally:
        cursor.close()


def main(matches=None):
    """
    Entry point for raw Snowflake ingestion.
    If matches are not provided in-memory, loads from data/raw/season_2025_2026.json.
    """
    if matches is None:
        if not DEFAULT_RAW_FILE.exists():
            raise FileNotFoundError(f"Raw data file not found: {DEFAULT_RAW_FILE}")

        with open(DEFAULT_RAW_FILE, "r") as f:
            raw_data = json.load(f)
            matches = raw_data.get("matches", [])

    conn = get_snowflake_connection()
    try:
        count = load_raw_matches(conn, matches)
        return count
    finally:
        conn.close()


if __name__ == "__main__":
    main()
