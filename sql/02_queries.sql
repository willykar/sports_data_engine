SELECT 
    f.match_date::date AS match_day,
    home.team_name AS home_team,
    away.team_name AS away_team_id,
    f.home_score,
    f.away_score,
    f.status
FROM sports_data_engine.fact_matches AS f
INNER JOIN sports_data_engine.dim_teams AS home
    ON f.home_team_id = home.team_id
INNER JOIN sports_data_engine.dim_teams AS away
    ON f.away_team_id = away.team_id
ORDER BY f.match DESC
LIMIT 10;