import pytest
import pandas as pd
from sqlalchemy import TIMESTAMP

from src.load import load_staging_tables, upsert_teams, upsert_matches, load_to_database
from unittest.mock import Mock, MagicMock, patch


def test_load_staging_tables_writes_both_staging_tables():
    dim_teams_df = pd.DataFrame({
        "team_id": [57, 64],
        "team_name": ["Arsenal FC", "Liverpool FC"]
    })

    fact_matches_df = pd.DataFrame({
        "match_id": [1001],
        "match_date": pd.to_datetime(["2026-08-21T19:00:00Z"]),
        "home_team_id": [57],
        "away_team_id": [64],
        "home_score": [2],
        "away_score": [0],
        "status": ["FINISHED"]
    })

    engine = Mock()

    dim_teams_df.to_sql = Mock()
    fact_matches_df.to_sql = Mock()

    load_staging_tables(
        dim_teams_df,
        fact_matches_df,
        engine
    )

    dim_teams_df.to_sql.assert_called_once_with(
        "stg_dim_teams",
        engine,
        schema="sports_data_engine",
        if_exists="replace",
        index=False
    )

   
    fact_matches_df.to_sql.assert_called_once()

    call_args = fact_matches_df.to_sql.call_args

    assert call_args.args[0] == "stg_fact_matches"
    assert call_args.args[1] is engine
    assert call_args.kwargs["schema"] == "sports_data_engine"
    assert call_args.kwargs["if_exists"] == "replace"
    assert call_args.kwargs["index"] is False
    assert isinstance(call_args.kwargs["dtype"]["match_date"], TIMESTAMP)

    

def test_upsert_teams_executes_insert_statement():
    conn = Mock()

    upsert_teams(conn)

    conn.execute.assert_called_once()

    sql = str(conn.execute.call_args.args[0])

    assert "INSERT INTO sports_data_engine.dim_teams" in sql
    assert "ON CONFLICT (team_id) DO NOTHING" in sql



def test_upsert_matches_executes_insert_update_statement():
    conn = Mock()

    upsert_matches(conn)

    conn.execute.assert_called_once()

    sql = str(conn.execute.call_args.args[0])

    assert "INSERT INTO sports_data_engine.fact_matches" in sql
    assert "ON CONFLICT (match_id)" in sql
    assert "DO UPDATE SET" in sql
    assert "home_score = EXCLUDED.home_score" in sql
    assert "away_score = EXCLUDED.away_score" in sql
    assert "status = EXCLUDED.status" in sql



def test_load_to_database_runs_transaction_steps():
    engine = MagicMock()
    conn = Mock()

    engine.begin.return_value.__enter__.return_value = conn

    conn.execute.side_effect = [
        Mock(scalar_one=Mock(return_value=20)),
        Mock(scalar_one=Mock(return_value=380)),
        None,
        None,
    ]

    with patch("src.load.upsert_teams") as mock_upsert_teams, \
         patch("src.load.upsert_matches") as mock_upsert_matches:

        load_to_database(engine)

    engine.begin.assert_called_once()
    mock_upsert_teams.assert_called_once_with(conn)
    mock_upsert_matches.assert_called_once_with(conn)

    assert conn.execute.call_count == 4


def test_load_to_database_rolls_back_when_upsert_fails():
    engine = MagicMock()
    conn = Mock()

    engine.begin.return_value.__enter__.return_value = conn

    conn.execute.side_effect = [
        Mock(scalar_one=Mock(return_value=20)),
        Mock(scalar_one=Mock(return_value=380)),
    ]

    with patch("src.load.upsert_teams", side_effect=Exception("upsert failed")):

        with pytest.raises(Exception, match="upsert failed"):
            load_to_database(engine)

    engine.begin.return_value.__exit__.assert_called_once()
    assert engine.begin.return_value.__exit__.call_args.args[0] is not None

