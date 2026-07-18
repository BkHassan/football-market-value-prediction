from pathlib import Path
import pandas as pd
import sys


def main():
    root = Path(__file__).resolve().parent.parent
    raw = root / 'data' / 'raw'
    processed = root / 'data' / 'processed'
    processed.mkdir(parents=True, exist_ok=True)

    players_fp = raw / 'sofascore_database_globale.csv'
    stats_fp = raw / 'sofascore_top5leagues_players_stat.csv'

    if not players_fp.exists():
        print(f"Fichier introuvable: {players_fp}")
        sys.exit(1)
    if not stats_fp.exists():
        print(f"Fichier introuvable: {stats_fp}")
        sys.exit(1)

    print(f"Lecture: {players_fp.name} and {stats_fp.name}")
    players = pd.read_csv(players_fp)
    stats = pd.read_csv(stats_fp)

    # Nettoyage basique des noms
    players['name_clean'] = players.get('name', players.columns[0]).astype(str).str.lower().str.strip()
    # stats file may use 'Nom' as column
    if 'Nom' in stats.columns:
        stats['name_clean'] = stats['Nom'].astype(str).str.lower().str.strip()
    elif 'name' in stats.columns:
        stats['name_clean'] = stats['name'].astype(str).str.lower().str.strip()
    else:
        stats['name_clean'] = stats.iloc[:, 0].astype(str).str.lower().str.strip()

    merged = pd.merge(players, stats, on='name_clean', how='inner')

    # Drop some common redundant columns if present
    to_drop = ['name_clean', 'Nom', 'Ligue', 'Equipe']
    for c in to_drop:
        if c in merged.columns:
            merged.drop(columns=[c], inplace=True, errors='ignore')

    # Reorder to keep important columns if they exist
    preferred = [
        'player_id', 'name', 'position', 'age', 'country', 'Buts', 'xG', 'Succ_dribbles',
        'Tacles', 'Assists', 'Passes_Reussies_Pct', 'club', 'league', 'market_value_raw'
    ]
    cols = [c for c in preferred if c in merged.columns]
    if cols:
        merged = merged[cols + [c for c in merged.columns if c not in cols]]

    out_fp = processed / 'dataset_final.csv'
    merged.to_csv(out_fp, index=False, encoding='utf-8-sig')
    print(f"Dataset fusionné écrit: {out_fp} (rows={len(merged)}, cols={len(merged.columns)})")


if __name__ == '__main__':
    main()
