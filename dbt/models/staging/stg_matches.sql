with source as (
    select * from {{ source('raw', 'raw_matches') }}
),

flattened as (
    select
        (payload:id)::NUMBER as match_id,
        (payload:utcDate)::TIMESTAMP_NTZ as match_date,
        (payload:status)::VARCHAR as status,
        (payload:homeTeam:id)::NUMBER as home_team_id,
        (payload:homeTeam:name)::VARCHAR as home_team_name,
        (payload:awayTeam:id)::NUMBER as away_team_id,
        (payload:awayTeam:name)::VARCHAR as away_team_name,
        -- Upcoming / scheduled fixtures have null scores; Snowflake JSON treats null as SQL NULL
        (payload:score:fullTime:home)::NUMBER as home_score,
        (payload:score:fullTime:away)::NUMBER as away_score,
        loaded_at
    from source
)

select * from flattened
