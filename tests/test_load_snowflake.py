import pytest
from unittest.mock import Mock, patch, mock_open
import json

from src.load_raw_snowflake import (
    get_snowflake_config,
    load_raw_matches,
    main,
)


def test_get_snowflake_config_raises_when_credentials_missing():
    with patch("src.load_raw_snowflake.getenv", return_value=None):
        with pytest.raises(ValueError, match="Missing required Snowflake environment variable"):
            get_snowflake_config()


def test_get_snowflake_config_returns_dict_when_configured():
    fake_env = {
        "SNOWFLAKE_ACCOUNT": "test_account",
        "SNOWFLAKE_USER": "test_user",
        "SNOWFLAKE_PASSWORD": "test_password",
        "SNOWFLAKE_ROLE": "TEST_ROLE",
        "SNOWFLAKE_WAREHOUSE": "TEST_WH",
        "SNOWFLAKE_DATABASE": "TEST_DB",
        "SNOWFLAKE_SCHEMA": "RAW",
    }
    with patch("src.load_raw_snowflake.getenv", side_effect=lambda k, default=None: fake_env.get(k, default)):
        config = get_snowflake_config()
        assert config["account"] == "test_account"
        assert config["user"] == "test_user"
        assert config["database"] == "TEST_DB"
        assert config["schema"] == "RAW"


def test_load_raw_matches_returns_zero_on_empty_payload():
    conn = Mock()
    result = load_raw_matches(conn, [])
    assert result == 0
    conn.cursor.assert_not_called()


def test_load_raw_matches_executes_staging_and_merge():
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value = cursor

    sample_matches = [
        {"id": 1001, "utcDate": "2026-08-21T19:00:00Z", "status": "FINISHED"},
        {"id": 1002, "utcDate": "2026-08-22T14:00:00Z", "status": "SCHEDULED"},
    ]

    count = load_raw_matches(conn, sample_matches)

    assert count == 2
    cursor.execute.assert_any_call("""
            CREATE TEMPORARY TABLE IF NOT EXISTS stg_raw_matches (
                match_id NUMBER,
                payload_str VARCHAR
            );
        """)
    cursor.executemany.assert_called_once()
    sql, params = cursor.executemany.call_args[0]
    assert "INSERT INTO stg_raw_matches" in sql
    assert len(params) == 2
    assert params[0][0] == 1001
    assert "1001" in params[0][1]

    # Verify MERGE execution
    merge_called = any("MERGE INTO RAW_MATCHES" in str(call) for call in cursor.execute.call_args_list)
    assert merge_called

    # Verify drop staging and commit
    drop_called = any("DROP TABLE IF EXISTS stg_raw_matches" in str(call) for call in cursor.execute.call_args_list)
    assert drop_called
    conn.commit.assert_called_once()
    cursor.close.assert_called_once()


def test_load_raw_matches_rolls_back_on_error():
    conn = Mock()
    cursor = Mock()
    conn.cursor.return_value = cursor
    cursor.execute.side_effect = Exception("Snowflake query execution error")

    sample_matches = [{"id": 1001, "utcDate": "2026-08-21T19:00:00Z"}]

    with pytest.raises(Exception, match="Snowflake query execution error"):
        load_raw_matches(conn, sample_matches)

    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()
    cursor.close.assert_called_once()


def test_main_with_in_memory_matches():
    mock_conn = Mock()
    sample_matches = [{"id": 1001, "status": "FINISHED"}]

    with patch("src.load_raw_snowflake.get_snowflake_connection", return_value=mock_conn), \
         patch("src.load_raw_snowflake.load_raw_matches", return_value=1) as mock_load:
        count = main(matches=sample_matches)
        assert count == 1
        mock_load.assert_called_once_with(mock_conn, sample_matches)
        mock_conn.close.assert_called_once()
