import pipeline


def _stages(target):
    return [stage for _, stage in pipeline.select_stages(target)]


def test_postgres_target_runs_postgres_stages_only():
    assert _stages("postgres") == [stage for _, stage in pipeline.POSTGRES_STAGES]


def test_snowflake_target_runs_snowflake_stages_only():
    assert _stages("snowflake") == [stage for _, stage in pipeline.SNOWFLAKE_STAGES]


def test_all_target_extracts_only_once():
    stages = _stages("all")
    assert stages.count(pipeline.run_extract) == 1
    assert stages[0] is pipeline.run_extract


def test_all_target_keeps_every_other_stage_in_order():
    stages = _stages("all")
    assert stages == [
        pipeline.run_extract,
        pipeline.run_transform,
        pipeline.run_load,
        pipeline.run_report,
        pipeline.run_load_snowflake,
        stages[-1],
    ]
