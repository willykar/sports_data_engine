from json import load
import pandas as pd
from pathlib import Path

def validate_data(dim_teams, fact_matches):
    print("Running data quality check....")

    # Dimesnsion table checks
    #check 1: team_id cannot be null
    if dim_teams["team_id"].isna().any():
        raise ValueError("dim_teams contains missing team_id values")

    #check 2: team_id must be unique
    if dim_teams["team_id"].duplicated().any():
        raise ValueError("dim_teams contains duplicate team_id values")

    #check 3: team_name cannot be NULL
    if dim_teams["team_name"].isna().any():
        raise ValueError("dim_teams contains missing team_name values")

    #check 4: team_name should not be empty
    if dim_teams["team_name"].astype(str).str.strip().eq("").any():
        raise ValueError("dim_teams contains empty team_name values")

    #check 5: match_id cannot be Null
    if fact_matches["match_id"].isna().any():
        raise ValueError("fact_matches contains missing match_id values")

    #check 6: match_id must be unique
    if fact_matches["match_id"].duplicated().any():
        raise ValueError("fact_matches contains duplicate match_id values")

    #check 7: match_date cannot be NULL
    if fact_matches["match_date"].isna().any():
        raise ValueError("fact_matches contains missing match_date values")

    # check 8: home_team_id cannot be null
    if fact_matches["home_team_id"].isna().any():
        raise ValueError("fact_matches contains missing home_team_id values")

    # check 9. away_team_id cannot be NULL
    if fact_matches["away_team_id"].isna().any():
        raise ValueError(
            "fact_matches contains missing away_team_id values"
        )

    # Check 10: status cannot be missing
    if fact_matches["status"].isna().any():
        raise ValueError("fact_matches contains missing status values")

    #check 11: check that match_date 
    if not pd.api.types.is_datetime64_any_dtype(fact_matches["match_date"]):
        raise ValueError("fact_matches match_date is not a datetime type")

    # --------------------------------------------------
    # REFERENTIAL INTEGRITY CHECKS
    # --------------------------------------------------

    # Get all valid team IDs from dim_teams
    valid_team_ids = set(dim_teams["team_id"])

    # check 10. Every home_team_id must exist in dim_teams
    invalid_home_teams = set(
        fact_matches["home_team_id"]
    ) - valid_team_ids

    if invalid_home_teams:
        raise ValueError(
            f"fact_matches contains home_team_id values "
            f"that do not exist in dim_teams: {invalid_home_teams}"
        )

    # check 11. Every away_team_id must exist in dim_teams
    invalid_away_teams = set(
        fact_matches["away_team_id"]
    ) - valid_team_ids

    if invalid_away_teams:
        raise ValueError(
            f"fact_matches contains away_team_id values "
            f"that do not exist in dim_teams: {invalid_away_teams}"
        )

    # --------------------------------------------------
    # MATCH LOGIC CHECKS
    # --------------------------------------------------

    # check 12. A team cannot play against itself
    same_team = (
        fact_matches["home_team_id"]
        == fact_matches["away_team_id"]
    )

    if same_team.any():
        raise ValueError(
            "fact_matches contains matches where "
            "home_team_id and away_team_id are the same"
        )

    # check 13. Scores cannot be negative
    if (
        fact_matches["home_score"].dropna() < 0
    ).any():
        raise ValueError(
            "fact_matches contains negative home scores"
        )

    if (
        fact_matches["away_score"].dropna() < 0
    ).any():
        raise ValueError(
            "fact_matches contains negative away scores"
        )

    # --------------------------------------------------
    # STATUS CHECK
    # --------------------------------------------------

    valid_statuses = {
        "SCHEDULED",
        "TIMED",
        "IN_PLAY",
        "PAUSED",
        "FINISHED",
        "POSTPONED",
        "SUSPENDED",
        "CANCELLED"
    }

    invalid_statuses = set(
        fact_matches["status"].dropna()
    ) - valid_statuses

    if invalid_statuses:
        raise ValueError(
            f"fact_matches contains invalid status values: "
            f"{invalid_statuses}"
        )


    print("All data quality checks passed!")


# define paths (Reading from raw, eventually writing to processed)
BASE_DIR =Path(__file__).resolve().parent.parent
RAW_FILE = BASE_DIR / 'data'/'raw'/'season_2025_2026.json'

# 2 load the raw data from disk
with open(RAW_FILE, 'r') as file:
    raw_data = load(file)

matches_list = raw_data.get('matches', [])
print(f'Loaded {len(matches_list)} matches for transformation')

# # Transfrom: Flatten the nested JSON into a structured list of dictionaries
match_records = []
for match in matches_list:
    # we are extracting ONLY the data we need for our realtional table
    record = {
        'match_id': match.get('id'),
        'match_date': match.get('utcDate'),
        'home_team_id': match['homeTeam'].get('id'),
        'home_team_name': match['homeTeam'].get('name'),
        'away_team_id': match['awayTeam'].get('id'),
        'away_team_name': match['awayTeam'].get('name'),
        'home_score': match['score']['fullTime'].get('home'),
        'away_score': match['score']['fullTime'].get('away'),
        'status': match.get('status')
    }

    match_records.append(record)

#4 laod into a PandasDataframe for easy viewing and future SQL injection
df_matches = pd.DataFrame(match_records)

# convert the date column
df_matches['match_date'] = pd.to_datetime(df_matches['match_date'])

#5 Inspect our new, flat, database-ready structure
print('\nTransformed Data Preview')
print(df_matches.head())
print('\nData Types:')
print(df_matches.dtypes)

# --- DIMENSION TABLE: dim_teams ---
home_teams = df_matches[['home_team_id', 'home_team_name']]

away_teams = df_matches[['away_team_id', 'away_team_name']]

# rename columns
home_teams = home_teams.rename(
    columns={
        'home_team_id':'team_id',
        'home_team_name': 'team_name'})

#rename coumns
away_teams = away_teams.rename(
    columns={
        'away_team_id':'team_id',
        'away_team_name': 'team_name'
    }
)

#stack them on top of each other
teams = pd.concat([home_teams, away_teams])

# drop duplicates
dim_teams = teams.drop_duplicates()

df_matches["home_score"] = pd.to_numeric(
    df_matches["home_score"],
    errors="coerce"
)

df_matches["away_score"] = pd.to_numeric(
    df_matches["away_score"],
    errors="coerce"
)


# fact_mathces
fact_matches = df_matches.drop(columns=['home_team_name', 'away_team_name'])

# Validate the transformed data
validate_data(dim_teams=dim_teams, fact_matches=fact_matches)

#--save TO DISK
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
# create a dictionary
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

dim_teams.to_csv(PROCESSED_DIR / 'dim_teams.csv', index=False)
fact_matches.to_csv(PROCESSED_DIR / 'fact_matches.csv', index=False)




