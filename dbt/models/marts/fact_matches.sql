with staged_matches as (
    select * from {{ ref('stg_matches') }}
)

select
    match_id,
    match_date,
    home_team_id,
    away_team_id,
    home_score,
    away_score,
    status
from staged_matches
