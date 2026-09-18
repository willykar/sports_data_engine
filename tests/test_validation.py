import pandas as pd
import pytest

from src.transform import validate_data


# ---------------------------------------------------------------------------
# Test Fixtures / Helper Data Generators
# ---------------------------------------------------------------------------
@pytest.fixture
def valid_teams() -> pd.DataFrame:
    """Generate a clean, valid sample DataFrame for dim_teams."""
    return pd.DataFrame({
        "team_id": [57, 64, 65],
        "team_name": [
            "Arsenal FC",
            "Liverpool FC",
            "Manchester City FC"
        ]
    })

@pytest.fixture
def valid_matches() -> pd.DataFrame:
    """Generate a clean, valid sample DataFrame for fact_matches."""
    return pd.DataFrame({
        "match_id": [1001, 1002],
        "match_date": pd.to_datetime([
            "2026-08-21T19:00:00Z",
            "2026-08-22T14:00:00Z"
        ]),
        "home_team_id": [57, 64],
        "away_team_id": [65, 57],
        "home_score": [2, 1],
        "away_score": [0, 2],
        "status": ["FINISHED", "FINISHED"]
    })


# ---------------------------------------------------------------------------
# Happy Path Tests
# ---------------------------------------------------------------------------

def test_valid_data_passes(valid_teams, valid_matches):
    """Verify that completely valid DataFrames pass all checks without error."""

    # Should execute cleanly without raising any exceptions
    validate_data(valid_teams, valid_matches)


# ---------------------------------------------------------------------------
# Primary Key & Uniqueness Constraints
# ---------------------------------------------------------------------------

def test_duplicate_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when dim_teams has duplicate primary keys."""

    # Inject duplicate team_id (57) into row index 1
    valid_teams.loc[1, "team_id"] = 57

    with pytest.raises(ValueError, match="duplicate team_id"):
        validate_data(valid_teams, valid_matches)


def test_missing_match_id_fails(valid_teams, valid_matches):
    """Verify rejection when fact_matches has a null match_id."""

    # Inject missing primary key
    valid_matches.loc[0, "match_id"] = None

    with pytest.raises(ValueError, match="missing match_id"):
        validate_data(valid_teams, valid_matches)


def test_missing_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when dim_teams has a null primary key."""

    # Inject missing team_id in dimension table
    valid_teams.loc[0, "team_id"] = None

    with pytest.raises(ValueError, match="missing team_id values"):
        validate_data(valid_teams, valid_matches)


# ---------------------------------------------------------------------------
# Referential Integrity / Foreign Key Constraints
# ---------------------------------------------------------------------------

def test_invalid_home_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when home_team_id does not exist in dim_teams."""

    # Set home_team_id to an orphaned key that is absent in dim_teams
    valid_matches.loc[0, "home_team_id"] = 9999999999999

    with pytest.raises(
        ValueError,
        match="home_team_id values that do not exist in dim_teams"
    ):
        validate_data(valid_teams, valid_matches)


def test_invalid_away_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when away_team_id does not exist in dim_teams."""

    # Set away_team_id to an orphaned key that is absent in dim_teams
    valid_matches.loc[0, "away_team_id"] = 999999

    with pytest.raises(
        ValueError,
        match="away_team_id values that do not exist in dim_teams"
    ):
        validate_data(valid_teams, valid_matches)


# ---------------------------------------------------------------------------
# Business Logic & Value Constraints
# ---------------------------------------------------------------------------

def test_negative_home_score_fails(valid_teams, valid_matches):
    """Verify rejection when home_score is negative."""
  

    # Inject negative score
    valid_matches.loc[0, "home_score"] = -1

    with pytest.raises(ValueError, match="negative home scores"):
        validate_data(valid_teams, valid_matches)


def test_negative_away_score_fails(valid_teams, valid_matches):
    """Verify rejection when away_score is negative."""
    

    # Inject negative score
    valid_matches.loc[0, "away_score"] = -1

    with pytest.raises(ValueError, match="negative away scores"):
        validate_data(valid_teams, valid_matches)


def test_inavlid_status_fails(valid_teams, valid_matches):
    """Verify rejection when status is not in the allowed enumeration."""

    # Inject an unrecognised fixture status
    valid_matches.loc[0, "status"] = "INVALID_STATUS"

    with pytest.raises(ValueError, match="invalid status values"):
        validate_data(valid_teams, valid_matches)


def test_same_home_and_away_team_fails(valid_teams, valid_matches):
    """Verify rejection when a team is scheduled to play against itself."""

    # Assign identical IDs to both home and away fields
    valid_matches.loc[0, "away_team_id"] = valid_matches.loc[0, "home_team_id"]

    with pytest.raises(
        ValueError,
        match="home_team_id and away_team_id are the same"
    ):
        validate_data(valid_teams, valid_matches)


# ---------------------------------------------------------------------------
# Null / Missing Value Checks
# ---------------------------------------------------------------------------

def test_missing_team_name_fails(valid_teams, valid_matches):
    """Verify rejection when team_name is null in dim_teams."""

    # Inject missing string value in dimension table
    valid_teams.loc[0, "team_name"] = None

    with pytest.raises(ValueError, match="missing team_name values"):
        validate_data(valid_teams, valid_matches)


def test_missing_match_date_fails(valid_teams, valid_matches):
    """Verify rejection when match_date is null in fact_matches."""

    # Inject missing timestamp
    valid_matches.loc[0, "match_date"] = None

    with pytest.raises(ValueError, match="missing match_date values"):
        validate_data(valid_teams, valid_matches)


def test_missing_home_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when home_team_id is null in fact_matches."""

    # Inject missing foreign key
    valid_matches.loc[0, "home_team_id"] = None

    with pytest.raises(ValueError, match="missing home_team_id values"):
        validate_data(valid_teams, valid_matches)


def test_missing_away_team_id_fails(valid_teams, valid_matches):
    """Verify rejection when away_team_id is null in fact_matches."""

    # Inject missing foreign key
    valid_matches.loc[0, "away_team_id"] = None

    with pytest.raises(ValueError, match="missing away_team_id values"):
        validate_data(valid_teams, valid_matches)


def test_missing_status_fails(valid_teams, valid_matches):
    """Verify rejection when fixture status is null in fact_matches."""

    # Inject missing status
    valid_matches.loc[0, "status"] = None

    with pytest.raises(ValueError, match="missing status values"):
        validate_data(valid_teams, valid_matches)


# ---------------------------------------------------------------------------
# Data Type & Schema Validation
# ---------------------------------------------------------------------------

def test_invalid_match_date_type_fails(valid_teams, valid_matches):
    """Verify rejection when match_date is not parsed as a proper datetime dtype."""

    # Cast datetime series to raw string to trigger type failure
    valid_matches["match_date"] = valid_matches["match_date"].astype(str)

    with pytest.raises(
        ValueError,
        match="match_date is not a datetime type"
    ):
        validate_data(valid_teams, valid_matches)