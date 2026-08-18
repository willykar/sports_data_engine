CREATE SCHEMA IF NOT EXISTS sports_data_engine;

CREATE TABLE IF NOT EXISTS sports_data_engine.dim_teams(
    team_id INTEGER PRIMARY KEY,

    team_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS sports_data_engine.fact_matches(
    match_id INTEGER PRIMARY KEY,

    home_team_id INTEGER NOT NULL REFERENCES sports_data_engine.dim_teams(team_id),

    away_team_id INTEGER NOT NULL REFERENCES sports_data_engine.dim_teams(team_id),

    home_score INTEGER,

    away_score INTEGER,

    status TEXT NOT NULL,

    match_date TIMESTAMP NOT NULL

);