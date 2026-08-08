"""
ETL: CSV files -> PostgreSQL

Pipeline (Extract -> Transform -> Load):
1. Extract  : read cleaned source CSVs from data/raw
2. Transform: normalize columns, cast types, merge for modeling
3. Load     : write three tables into PostgreSQL with SQLAlchemy

Why SQLAlchemy + pandas?
- Simple enough for a student project
- pandas handles CSV cleaning well
- SQLAlchemy gives a clean DB connection string and to_sql() helper
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"

PLAYERS_CSV = RAW_DIR / "sofascore_database_globale.csv"
STATS_CSV = RAW_DIR / "sofascore_top5leagues_players_stat.csv"


def get_engine() -> Engine:
    """Build a SQLAlchemy engine from .env credentials."""
    load_dotenv(ROOT / ".env")

    user = os.getenv("POSTGRES_USER", "marketvalue")
    password = os.getenv("POSTGRES_PASSWORD", "marketvalue")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "marketvalue")

    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(url)


def clean_jersey_number(series: pd.Series) -> pd.Series:
    """Convert jersey numbers; SofaScore uses '-' when unknown."""
    cleaned = series.astype(str).str.strip().replace({"-": pd.NA, "nan": pd.NA, "None": pd.NA})
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def clean_market_value(series: pd.Series) -> pd.Series:
    """Cast market value strings/numbers to nullable integers (euros)."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


def extract_players(path: Path) -> pd.DataFrame:
    """Extract + lightly clean the players identity table."""
    df = pd.read_csv(path)

    out = pd.DataFrame(
        {
            "player_id": pd.to_numeric(df["player_id"], errors="coerce").astype("Int64"),
            "name": df["name"].astype(str).str.strip(),
            "short_name": df.get("short_name"),
            "position": df.get("position"),
            "jersey_number": clean_jersey_number(df["jersey_number"]) if "jersey_number" in df.columns else pd.NA,
            "age": pd.to_numeric(df.get("age"), errors="coerce"),
            "country": df.get("country"),
            "market_value": clean_market_value(df["market_value_raw"]) if "market_value_raw" in df.columns else pd.NA,
            "league": df.get("league").astype(str).str.strip().str.lower() if "league" in df.columns else None,
            "club": df.get("club").astype(str).str.strip().str.lower() if "club" in df.columns else None,
        }
    )

    # Drop rows without a usable primary key or name.
    out = out.dropna(subset=["player_id", "name"])
    out = out.drop_duplicates(subset=["player_id"], keep="first")
    return out


def extract_stats(path: Path) -> pd.DataFrame:
    """Extract + rename French CSV columns to a clean English schema."""
    df = pd.read_csv(path)

    # Source CSV uses French headers (Ligue, Equipe, Nom, ...).
    rename_map = {
        "Ligue": "league",
        "Equipe": "team",
        "Nom": "player_name",
        "Buts": "goals",
        "xG": "xg",
        "Succ_dribbles": "successful_dribbles",
        "Tacles": "tackles",
        "Assists": "assists",
        "Passes_Reussies_Pct": "pass_accuracy_pct",
    }
    df = df.rename(columns=rename_map)

    out = pd.DataFrame(
        {
            "league": df["league"].astype(str).str.strip() if "league" in df.columns else None,
            "team": df["team"].astype(str).str.strip() if "team" in df.columns else None,
            "player_name": df["player_name"].astype(str).str.strip(),
            "goals": pd.to_numeric(df.get("goals"), errors="coerce").fillna(0).astype(int),
            "xg": pd.to_numeric(df.get("xg"), errors="coerce"),
            "successful_dribbles": pd.to_numeric(df.get("successful_dribbles"), errors="coerce").fillna(0).astype(int),
            "tackles": pd.to_numeric(df.get("tackles"), errors="coerce").fillna(0).astype(int),
            "assists": pd.to_numeric(df.get("assists"), errors="coerce").fillna(0).astype(int),
            "pass_accuracy_pct": pd.to_numeric(df.get("pass_accuracy_pct"), errors="coerce"),
        }
    )

    out = out.dropna(subset=["player_name"])
    # Keep one row per player name for a stable merge (same idea as the CSV ETL).
    out = out.drop_duplicates(subset=["player_name"], keep="first")
    return out


def build_players_ml(players: pd.DataFrame, stats: pd.DataFrame) -> pd.DataFrame:
    """
    Build the modeling table by joining players and stats on cleaned names.

    Why merge here?
    - players has market_value / player_id
    - stats has goals / xG / assists / ...
    - ML models need both in one flat table
    """
    left = players.copy()
    right = stats.copy()

    left["name_clean"] = left["name"].astype(str).str.lower().str.strip()
    right["name_clean"] = right["player_name"].astype(str).str.lower().str.strip()

    merged = left.merge(
        right[
            [
                "name_clean",
                "goals",
                "xg",
                "successful_dribbles",
                "tackles",
                "assists",
                "pass_accuracy_pct",
            ]
        ],
        on="name_clean",
        how="inner",
    )

    out = merged[
        [
            "player_id",
            "name",
            "short_name",
            "position",
            "jersey_number",
            "age",
            "country",
            "goals",
            "xg",
            "successful_dribbles",
            "tackles",
            "assists",
            "pass_accuracy_pct",
            "club",
            "league",
            "market_value",
        ]
    ].copy()

    out = out.drop_duplicates(subset=["player_id"], keep="first")
    return out


def load_table(df: pd.DataFrame, table_name: str, engine: Engine) -> None:
    """
    Replace table contents safely:
    1) TRUNCATE (keeps schema/constraints created by db/init)
    2) append rows with pandas.to_sql
    """
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_name} RESTART IDENTITY CASCADE"))

    # Convert pandas nullable ints to object/float so psycopg2 accepts NaN -> NULL.
    upload = df.copy()
    for col in upload.columns:
        if str(upload[col].dtype) == "Int64":
            upload[col] = upload[col].astype(object).where(upload[col].notna(), None)

    upload.to_sql(table_name, engine, if_exists="append", index=False, method="multi", chunksize=500)
    print(f"Loaded {len(upload)} rows into '{table_name}'")


def save_processed_csv(players_ml: pd.DataFrame) -> Path:
    """Also refresh data/processed/dataset_final.csv for notebooks that still use CSV."""
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out_fp = PROCESSED_DIR / "dataset_final.csv"

    # Keep notebook-friendly column names close to the previous CSV ETL output.
    export = players_ml.rename(
        columns={
            "goals": "Buts",
            "xg": "xG",
            "successful_dribbles": "Succ_dribbles",
            "tackles": "Tacles",
            "assists": "Assists",
            "pass_accuracy_pct": "Passes_Reussies_Pct",
            "market_value": "market_value_raw",
        }
    )
    export.to_csv(out_fp, index=False, encoding="utf-8-sig")
    print(f"Updated processed CSV: {out_fp}")
    return out_fp


def main() -> None:
    if not PLAYERS_CSV.exists():
        print(f"Missing file: {PLAYERS_CSV}")
        sys.exit(1)
    if not STATS_CSV.exists():
        print(f"Missing file: {STATS_CSV}")
        sys.exit(1)

    print("Extracting CSVs...")
    players = extract_players(PLAYERS_CSV)
    stats = extract_stats(STATS_CSV)
    players_ml = build_players_ml(players, stats)

    print(f"players rows     : {len(players)}")
    print(f"player_stats rows: {len(stats)}")
    print(f"players_ml rows  : {len(players_ml)}")

    print("Connecting to PostgreSQL...")
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    print("Loading tables...")
    load_table(players, "players", engine)
    load_table(stats, "player_stats", engine)
    load_table(players_ml, "players_ml", engine)

    save_processed_csv(players_ml)

    # Quick sanity checks useful for a portfolio demo.
    with engine.connect() as conn:
        for table in ("players", "player_stats", "players_ml"):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
            print(f"DB check: {table} = {count} rows")

    print("ETL finished successfully.")


if __name__ == "__main__":
    main()
