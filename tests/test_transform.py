import pandas as pd

from src.transform import transform_matches, build_dim_teams, build_fact_matches


def test_transform_matches_creates_expected_columns():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df = transform_matches(matches)

    assert list(df.columns) == [
        "match_id",
        "match_date",
        "home_team_id",
        "home_team_name",
        "away_team_id",
        "away_team_name",
        "home_score",
        "away_score",
        "status"
    ]

def test_transform_matches_transforms_values_correctly():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df = transform_matches(matches)

    row = df.iloc[0]

    assert row["match_id"] == 1
    assert row["home_team_id"] == 10
    assert row["home_team_name"] == "Team A"
    assert row["away_team_id"] == 20
    assert row["away_team_name"] == "Team B"
    assert row["home_score"] == 2
    assert row["away_score"] == 1
    assert row["status"] == "FINISHED"
    assert isinstance(row["match_date"], pd.Timestamp)

def test_transform_matches_handles_missing_scores():
    matches = [
        {
            "id": 2,
            "utcDate": "2026-09-01T19:00:00Z",
            "homeTeam": {"id": 30, "name": "Team C"},
            "awayTeam": {"id": 40, "name": "Team D"},
            "score": {
                "fullTime": {
                    "home": None,
                    "away": None
                }
            },
            "status": "SCHEDULED"
        }
    ]

    df = transform_matches(matches)

    assert pd.isna(df.iloc[0]["home_score"])
    assert pd.isna(df.iloc[0]["away_score"])

def test_transform_matches_handles_multiple_matches():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        },
        {
            "id": 2,
            "utcDate": "2026-08-22T14:00:00Z",
            "homeTeam": {"id": 30, "name": "Team C"},
            "awayTeam": {"id": 40, "name": "Team D"},
            "score": {
                "fullTime": {
                    "home": None,
                    "away": None
                }
            },
            "status": "SCHEDULED"
        }
    ]

    df = transform_matches(matches)

    assert len(df) == 2
    assert df.iloc[0]["match_id"] == 1
    assert df.iloc[1]["match_id"] == 2


def test_transform_matches_converts_match_date_to_datetime():
    matches = [
        {
            "id": 3,
            "utcDate": "2026-08-23T15:30:00Z",
            "homeTeam": {"id": 50, "name": "Team E"},
            "awayTeam": {"id": 60, "name": "Team F"},
            "score": {
                "fullTime": {
                    "home": 1,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df = transform_matches(matches)

    assert pd.api.types.is_datetime64_any_dtype(df["match_date"])


def test_transform_matches_converts_scores_to_numeric():
    matches = [
        {
            "id": 4,
            "utcDate": "2026-08-24T18:00:00Z",
            "homeTeam": {"id": 70, "name": "Team G"},
            "awayTeam": {"id": 80, "name": "Team H"},
            "score": {
                "fullTime": {
                    "home": "3",
                    "away": "2"
                }
            },
            "status": "FINISHED"
        }
    ]

    df = transform_matches(matches)

    assert df.iloc[0]["home_score"] == 3
    assert df.iloc[0]["away_score"] == 2
    assert pd.api.types.is_numeric_dtype(df["home_score"])
    assert pd.api.types.is_numeric_dtype(df["away_score"])

def test_transform_matches_invalid_scores_become_missing():
    matches = [
        {
            "id": 5,
            "utcDate": "2026-08-25T18:00:00Z",
            "homeTeam": {"id": 90, "name": "Team I"},
            "awayTeam": {"id": 100, "name": "Team J"},
            "score": {
                "fullTime": {
                    "home": "unknown",
                    "away": "1"
                }
            },
            "status": "FINISHED"
        }
    ]

    df = transform_matches(matches)

    assert pd.isna(df.iloc[0]["home_score"])
    assert df.iloc[0]["away_score"] == 1

def test_build_dim_teams_removes_duplicate_teams():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {"fullTime": {"home": 2, "away": 1}},
            "status": "FINISHED"
        },
        {
            "id": 2,
            "utcDate": "2026-08-22T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 30, "name": "Team C"},
            "score": {"fullTime": {"home": 1, "away": 0}},
            "status": "FINISHED"
        }
    ]

    df_matches = transform_matches(matches)

    dim_teams = build_dim_teams(df_matches)

    assert len(dim_teams) == 3
    assert set(dim_teams["team_id"]) == {10, 20, 30}

def test_build_dim_teams_preserves_team_names():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df_matches = transform_matches(matches)
    dim_teams = build_dim_teams(df_matches)

    team_names = dict(zip(dim_teams["team_id"], dim_teams["team_name"]))

    assert team_names[10] == "Team A"
    assert team_names[20] == "Team B"

def test_build_dim_teams_creates_expected_columns():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df_matches = transform_matches(matches)
    dim_teams = build_dim_teams(df_matches)

    assert list(dim_teams.columns) == ["team_id", "team_name"]


def test_build_fact_matches_creates_expected_columns():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df_matches = transform_matches(matches)

    fact_matches = build_fact_matches(df_matches)

    assert list(fact_matches.columns) == [
        "match_id",
        "match_date",
        "home_team_id",
        "away_team_id",
        "home_score",
        "away_score",
        "status"
    ]


def test_build_fact_matches_preserves_match_data():
    matches = [
        {
            "id": 1,
            "utcDate": "2026-08-21T19:00:00Z",
            "homeTeam": {"id": 10, "name": "Team A"},
            "awayTeam": {"id": 20, "name": "Team B"},
            "score": {
                "fullTime": {
                    "home": 2,
                    "away": 1
                }
            },
            "status": "FINISHED"
        }
    ]

    df_matches = transform_matches(matches)
    fact_matches = build_fact_matches(df_matches)

    row = fact_matches.iloc[0]

    assert row["match_id"] == 1
    assert row["match_date"] == pd.Timestamp("2026-08-21T19:00:00Z")
    assert row["home_team_id"] == 10
    assert row["away_team_id"] == 20
    assert row["home_score"] == 2
    assert row["away_score"] == 1
    assert row["status"] == "FINISHED"