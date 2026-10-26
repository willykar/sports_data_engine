-- Singular test: match scores must never be negative.
-- In dbt, a test passes if the query returns 0 rows.
select
    match_id,
    home_score,
    away_score
from {{ ref('fact_matches') }}
where home_score < 0
   or away_score < 0
