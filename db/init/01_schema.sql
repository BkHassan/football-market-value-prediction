-- Schema for SofaScore player market-value data.
--
-- Why define the schema in SQL?
-- - Clear types and constraints (better than guessing from CSV)
-- - Runs automatically when the Postgres container is created
-- - Easy for reviewers to understand the data model
--
-- Design choice (kept intentionally simple):
-- 1) players      -> identity + market value (from sofascore_database_globale.csv)
-- 2) player_stats -> season performance stats (from sofascore_top5leagues_players_stat.csv)
-- 3) players_ml   -> merged modeling table (same content as dataset_final.csv)

CREATE TABLE IF NOT EXISTS players (
    player_id       BIGINT PRIMARY KEY,
    name            TEXT NOT NULL,
    short_name      TEXT,
    position        VARCHAR(10),
    jersey_number   INTEGER,
    age             NUMERIC(4, 1),
    country         TEXT,
    market_value    BIGINT,
    league          TEXT,
    club            TEXT
);

CREATE TABLE IF NOT EXISTS player_stats (
    id                    SERIAL PRIMARY KEY,
    league                TEXT,
    team                  TEXT,
    player_name           TEXT NOT NULL,
    goals                 INTEGER,
    xg                    NUMERIC(8, 2),
    successful_dribbles   INTEGER,
    tackles               INTEGER,
    assists               INTEGER,
    pass_accuracy_pct     NUMERIC(5, 2)
);

CREATE TABLE IF NOT EXISTS players_ml (
    player_id             BIGINT PRIMARY KEY,
    name                  TEXT NOT NULL,
    short_name            TEXT,
    position              VARCHAR(10),
    jersey_number         INTEGER,
    age                   NUMERIC(4, 1),
    country               TEXT,
    goals                 INTEGER,
    xg                    NUMERIC(8, 2),
    successful_dribbles   INTEGER,
    tackles               INTEGER,
    assists               INTEGER,
    pass_accuracy_pct     NUMERIC(5, 2),
    club                  TEXT,
    league                TEXT,
    market_value          BIGINT
);

-- Helpful indexes for common filters used in analysis / notebooks.
CREATE INDEX IF NOT EXISTS idx_players_league ON players (league);
CREATE INDEX IF NOT EXISTS idx_players_club ON players (club);
CREATE INDEX IF NOT EXISTS idx_player_stats_name ON player_stats (player_name);
CREATE INDEX IF NOT EXISTS idx_players_ml_league ON players_ml (league);
