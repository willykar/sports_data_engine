from pathlib import Path
from os import getenv
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


BASE_DIR = Path(__file__).resolve().parent.parent


load_dotenv(BASE_DIR / '.env')

db_url = getenv("DB_URL")

if not db_url:
    raise ValueError("Database url is not set")

engine = create_engine(db_url)

schema_file = BASE_DIR / "sql" / "01_schema.sql"

with open(schema_file, 'r', encoding="utf-8") as file:
    schema_sql = file.read()

with engine.begin() as conn:
    conn.execute(text(schema_sql))

print("Database schema created successfully.")