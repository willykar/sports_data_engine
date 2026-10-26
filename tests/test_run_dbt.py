import pytest
from unittest.mock import patch, Mock
from pathlib import Path
from src.run_dbt import get_dbt_executable, run_dbt, main


def test_get_dbt_executable_returns_valid_path():
    exe_list = get_dbt_executable()
    assert len(exe_list) >= 1
    assert "dbt" in exe_list[0]


def test_run_dbt_calls_subprocess_with_project_dirs():
    with patch("src.run_dbt.subprocess.run") as mock_run:
        mock_run.return_value = Mock(returncode=0)

        returncode = run_dbt(command="run")

        assert returncode == 0
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "run" in cmd
        assert "--project-dir" in cmd
        assert "--profiles-dir" in cmd


def test_main_runs_dbt_build():
    with patch("src.run_dbt.run_dbt") as mock_run_dbt:
        main()
        mock_run_dbt.assert_called_once_with("build")
