-- Singular test: home_team_id and away_team_id must never be the same team.
-- In dbt, a test passes if the query returns 0 rows.
select
    match_id,
    home_team_id,
    away_team_id
from {{ ref('fact_matches') }}
where home_team_id = away_team_id
