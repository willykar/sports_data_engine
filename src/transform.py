from json import load
import pandas as pd
from pathlib import Path


def validate_data(dim_teams, fact_matches):
    print("Running data quality check....")

    # Dimension table checks

    if dim_teams["team_id"].isna().any():
        raise ValueError(
            "dim_teams contains missing team_id values"
        )

    if dim_teams["team_id"].duplicated().any():
        raise ValueError(
            "dim_teams contains duplicate team_id values"
        )

    if dim_teams["team_name"].isna().any():
        raise ValueError(
            "dim_teams contains missing team_name values"
        )

    if dim_teams["team_name"].astype(str).str.strip().eq("").any():
        raise ValueError(
            "dim_teams contains empty team_name values"
        )

    if fact_matches["match_id"].isna().any():
        raise ValueError(
            "fact_matches contains missing match_id values"
        )

    if fact_matches["match_id"].duplicated().any():
        raise ValueError(
            "fact_matches contains duplicate match_id values"
        )

    if fact_matches["match_date"].isna().any():
        raise ValueError(
            "fact_matches contains missing match_date values"
        )

    if fact_matches["home_team_id"].isna().any():
        raise ValueError(
            "fact_matches contains missing home_team_id values"
        )

    if fact_matches["away_team_id"].isna().any():
        raise ValueError(
            "fact_matches contains missing away_team_id values"
        )

    if fact_matches["status"].isna().any():
        raise ValueError(
            "fact_matches contains missing status values"
        )

    if not pd.api.types.is_datetime64_any_dtype(
        fact_matches["match_date"]
    ):
        raise ValueError(
            "fact_matches match_date is not a datetime type"
        )

    # Referential integrity

    valid_team_ids = set(dim_teams["team_id"])

    invalid_home_teams = (
        set(fact_matches["home_team_id"]) - valid_team_ids
    )

    if invalid_home_teams:
        raise ValueError(
            f"fact_matches contains home_team_id values "
            f"that do not exist in dim_teams: "
            f"{invalid_home_teams}"
        )

    invalid_away_teams = (
        set(fact_matches["away_team_id"]) - valid_team_ids
    )

    if invalid_away_teams:
        raise ValueError(
            f"fact_matches contains away_team_id values "
            f"that do not exist in dim_teams: "
            f"{invalid_away_teams}"
        )

    # Match logic

    same_team = (
        fact_matches["home_team_id"]
        == fact_matches["away_team_id"]
    )

    if same_team.any():
        raise ValueError(
            "fact_matches contains matches where "
            "home_team_id and away_team_id are the same"
        )

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

    # Status validation

    valid_statuses = {
        "SCHEDULED",
        "TIMED",
        "IN_PLAY",
        "PAUSED",
        "FINISHED",
        "POSTPONED",
        "SUSPENDED",
        "CANCELLED",
    }

    invalid_statuses = (
        set(fact_matches["status"].dropna())
        - valid_statuses
    )

    if invalid_statuses:
        raise ValueError(
            f"fact_matches contains invalid status values: "
            f"{invalid_statuses}"
        )

    print("All data quality checks passed!")


def transform_matches(matches_list):
    """
    Transform raw API match records into a flat DataFrame.
    """

    match_records = []

    for match in matches_list:
        record = {
            "match_id": match.get("id"),
            "match_date": match.get("utcDate"),
            "home_team_id": match["homeTeam"].get("id"),
            "home_team_name": match["homeTeam"].get("name"),
            "away_team_id": match["awayTeam"].get("id"),
            "away_team_name": match["awayTeam"].get("name"),
            "home_score": match["score"]["fullTime"].get("home"),
            "away_score": match["score"]["fullTime"].get("away"),
            "status": match.get("status"),
        }

        match_records.append(record)

    df_matches = pd.DataFrame(match_records)

    # Convert date
    df_matches["match_date"] = pd.to_datetime(
        df_matches["match_date"]
    )

    # Convert scores
    df_matches["home_score"] = pd.to_numeric(
        df_matches["home_score"],
        errors="coerce",
    )

    df_matches["away_score"] = pd.to_numeric(
        df_matches["away_score"],
        errors="coerce",
    )

    return df_matches

def build_dim_teams(df_matches):
    home_teams = df_matches[["home_team_id", "home_team_name"]].rename(
        columns={
            "home_team_id": "team_id",
            "home_team_name": "team_name"
        }
    )

    away_teams = df_matches[["away_team_id", "away_team_name"]].rename(
        columns={
            "away_team_id": "team_id",
            "away_team_name": "team_name"
        }
    )

    teams = pd.concat([home_teams, away_teams])

    return teams.drop_duplicates()

def build_fact_matches(df_matches):
    return df_matches.drop(
        columns=["home_team_name", "away_team_name"]
    )

def main():

    # Define paths
    BASE_DIR = Path(__file__).resolve().parent.parent

    RAW_FILE = (
        BASE_DIR
        / "data"
        / "raw"
        / "season_2025_2026.json"
    )

    # Load raw JSON
    with open(RAW_FILE, "r") as file:
        raw_data = load(file)

    matches_list = raw_data.get("matches", [])

    print(
        f"Loaded {len(matches_list)} matches for transformation"
    )

    # Transform raw data
    df_matches = transform_matches(matches_list)

    # Inspect transformed data
    print("\nTransformed Data Preview")
    print(df_matches.head())

    print("\nData Types:")
    print(df_matches.dtypes)


    # Create dimension table
    dim_teams = build_dim_teams(df_matches)
    
    # Create fact table
    fact_matches = build_fact_matches(df_matches)

    # Validate
    validate_data(
        dim_teams=dim_teams,
        fact_matches=fact_matches,
    )

    # Save processed data
    PROCESSED_DIR = (
        BASE_DIR / "data" / "processed"
    )

    PROCESSED_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    dim_teams.to_csv(
        PROCESSED_DIR / "dim_teams.csv",
        index=False,
    )

    fact_matches.to_csv(
        PROCESSED_DIR / "fact_matches.csv",
        index=False,
    )


if __name__ == "__main__":
    main()