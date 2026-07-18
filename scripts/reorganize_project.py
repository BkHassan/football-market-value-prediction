import argparse
import shutil
from pathlib import Path
from datetime import datetime


def backup_path(root: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = root / f"backup_{ts}"
    p.mkdir(parents=True, exist_ok=True)
    return p


def main(apply: bool):
    root = Path(__file__).resolve().parent.parent
    print(f"Project root: {root}")

    # Directories to create
    dirs = [root / 'data' / 'raw', root / 'data' / 'processed', root / 'notebooks', root / 'src', root / 'models']
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory: {d}")

    # Backup
    bkp = backup_path(root)
    print(f"Backup dir: {bkp}")

    # Rename folder with stray space if it exists
    bad_name = root / 'model_et_visualisation_des _donnees'
    good_name = root / 'model_et_visualisation_des_donnees'
    if bad_name.exists():
        print(f"Found folder with bad name: {bad_name}")
        if apply:
            shutil.copytree(bad_name, bkp / bad_name.name)
            bad_name.rename(good_name)
            print(f"Renamed {bad_name.name} -> {good_name.name}")
        else:
            print(f"Would rename {bad_name} -> {good_name}")

    # Move sofascore CSVs into data/raw
    scraping_dir = root / 'scraping_process'
    if scraping_dir.exists():
        csvs = list(scraping_dir.glob('sofascore_*.csv'))
        for f in csvs:
            target = root / 'data' / 'raw' / f.name
            print(f"Found CSV: {f} -> {target}")
            if apply:
                shutil.copy2(f, bkp / f.name)
                shutil.move(str(f), str(target))
        # Move aggregated database to processed if exists
        agg = scraping_dir / 'sofascore_database_globale.csv'
        if agg.exists():
            target = root / 'data' / 'processed' / agg.name
            print(f"Moving aggregated file: {agg} -> {target}")
            if apply:
                shutil.copy2(agg, bkp / agg.name)
                shutil.move(str(agg), str(target))

    # Move notebooks into notebooks/
    nb_sources = [root / 'scraping_process', good_name if good_name.exists() else bad_name if bad_name.exists() else None]
    for src in [p for p in nb_sources if p]:
        for nb in src.glob('*.ipynb'):
            target = root / 'notebooks' / nb.name
            print(f"Notebook: {nb} -> {target}")
            if apply:
                shutil.copy2(nb, bkp / nb.name)
                shutil.move(str(nb), str(target))

    print("Réorganisation terminée." if apply else "Dry-run terminé. Aucune modification appliquée.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Réorganiser la structure du projet (déplacer CSVs, notebooks, renommer dossiers)')
    parser.add_argument('--apply', action='store_true', help='Appliquer les changements. Sans ce flag, fait un dry-run.')
    args = parser.parse_args()
    main(args.apply)
