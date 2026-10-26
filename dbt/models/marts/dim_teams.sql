with staged_matches as (
    select * from {{ ref('stg_matches') }}
),

home_teams as (
    select distinct
        home_team_id as team_id,
        home_team_name as team_name
    from staged_matches
    where home_team_id is not null
),

away_teams as (
    select distinct
        away_team_id as team_id,
        away_team_name as team_name
    from staged_matches
    where away_team_id is not null
),

unioned as (
    select * from home_teams
    union
    select * from away_teams
)

select distinct
    team_id,
    team_name
from unioned
