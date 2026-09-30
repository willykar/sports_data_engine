import requests
from pathlib import Path
from json import dump
from os import getenv
from dotenv import load_dotenv

# Set path relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "raw" / "season_2025_2026.json"

URL = 'https://api.football-data.org/v4/competitions/PL/matches'


def fetch_matches(date_from=None, date_to=None):
    """
    Fetch the competition's matches and return the full parsed payload.

    Writes nothing. Pass date_from and date_to as YYYY-MM-DD to narrow the
    window -- the DAG's branch uses this to ask whether there are any fixtures
    worth running the pipeline for, at the cost of one small request.

    football-data.org requires the two dates together, so supplying only one
    is rejected here rather than by the API.
    """
    if (date_from is None) != (date_to is None):
        raise ValueError("date_from and date_to must be given together")

    load_dotenv(BASE_DIR / '.env')

    api_key = getenv('football_data_api_key')

    if not api_key:
        raise ValueError("football_data_api_key is not set")

    headers = {
        'X-Auth-Token': api_key
    }

    params = {}
    if date_from:
        params["dateFrom"] = date_from
        params["dateTo"] = date_to

    response = requests.get(URL, headers=headers, params=params or None)
    response.raise_for_status()

    return response.json()


def main():
    parsed_content = fetch_matches()

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
