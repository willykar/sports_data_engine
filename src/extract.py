import requests
from pathlib import Path
from json import dump
from os import getenv
from dotenv import load_dotenv

# Set path relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "raw" / "season_2025_2026.json"

URL = 'https://api.football-data.org/v4/competitions/PL/matches'


def main():
    load_dotenv(BASE_DIR / '.env')

    api_key = getenv('football_data_api_key')

    if not api_key:
        raise ValueError("football_data_api_key is not set")

    headers = {
        'X-Auth-Token': api_key
    }

    response = requests.get(URL, headers=headers)
    response.raise_for_status()

    parsed_content = response.json()

    matches = parsed_content.get("matches", [])
    print(f"Successfully fetched {len(matches)} matches.")

    ## print the keys of the first element in the matches
    if matches:
        print("Sample record keys:", list(matches[0].keys()))

    ## save the json
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as file:
        dump(parsed_content, file)

    print(f"Raw data saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
