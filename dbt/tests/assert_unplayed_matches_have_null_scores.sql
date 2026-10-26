-- Standing knowledge rule: A missing score is NULL, never 0.
-- Scheduled or timed fixtures must not have non-null scores.
-- In dbt, a test passes if the query returns 0 rows.
select
    match_id,
    status,
    home_score,
    away_score
from {{ ref('fact_matches') }}
where status in ('SCHEDULED', 'TIMED')
  and (home_score is not null or away_score is not null)
