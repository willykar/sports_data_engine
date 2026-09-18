from pathlib import Path
from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent.parent

SCHEMA_FILE = BASE_DIR / "sql" / "01_schema.sql"


def main():
    load_dotenv(BASE_DIR / '.env')

    db_url = getenv("DB_URL")

    if not db_url:
        raise ValueError("DB_URL is not set")

    engine = create_engine(db_url)

    with open(SCHEMA_FILE, 'r', encoding="utf-8") as file:
        schema_sql = file.read()

    with engine.begin() as conn:
        conn.execute(text(schema_sql))

    print("Database schema created successfully.")


if __name__ == "__main__":
    main()
