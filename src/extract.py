import requests
from pathlib import Path
from json import loads, dump
from os import getenv
from dotenv import load_dotenv

# Set path relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = BASE_DIR / "data" / "raw" / "season_2025_2026.json"


url = 'https://api.football-data.org/v4/competitions/PL/matches'

load_dotenv(BASE_DIR / '.env')

API_KEY = getenv('football_data_api_key')

headers = {
    'X-Auth-Token': f'{API_KEY}'
}

response = requests.get(url, headers=headers)
response.raise_for_status()

parsed_content = response.json()

matches = parsed_content.get("matches", [])
print(f"Successfully fetched {len(matches)} matches.")

## print the keys of the first element in the matches
if matches:
    print("Sample record keys:", list(matches[0].keys()))

# print(f'Type: {type(parsed_content["matches"])}')


## save the json
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
with open('./data/raw/season_2025_2026.json', 'w') as file:
    dump(parsed_content, file)

print(f"Raw data saved to: {OUTPUT_FILE}")

