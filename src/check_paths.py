import json
import argparse
import shutil
from pathlib import Path
from datetime import datetime


REPLACEMENTS = [
    # from, to (relative to notebooks folder)
    ("scraping_process/sofascore_database_globale.csv", "../data/processed/sofascore_database_globale.csv"),
    ("scraping_process/", "../data/raw/"),
    ("model_et_visualisation_des _donnees", "model_et_visualisation_des_donnees"),
]


def backup(orig: Path) -> Path:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    b = orig.parent / f"backup_notebooks_{ts}"
    b.mkdir(parents=True, exist_ok=True)
    return b


def process_notebook(nb_path: Path, apply: bool, bkp_dir: Path):
    data = json.loads(nb_path.read_text(encoding='utf-8'))
    changed = False
    replace_count = 0
    for cell in data.get('cells', []):
        if 'source' not in cell:
            continue
        new_src = []
        for line in cell['source']:
            new_line = line
            for old, new in REPLACEMENTS:
                if old in new_line:
                    new_line = new_line.replace(old, new)
                    changed = True
                    replace_count += 1
            new_src.append(new_line)
        cell['source'] = new_src

    if changed:
        print(f"{nb_path}: {replace_count} remplacements détectés")
        if apply:
            shutil.copy2(nb_path, bkp_dir / nb_path.name)
            nb_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')
            print(f"Modifié et sauvegardé: {nb_path}")
    return replace_count


def main(apply: bool):
    root = Path(__file__).resolve().parent.parent
    notebooks = root / 'notebooks'
    if not notebooks.exists():
        print(f"Dossier notebooks/ introuvable: {notebooks}")
        return
    bkp = backup(notebooks)
    total = 0
    for nb in notebooks.glob('*.ipynb'):
        total += process_notebook(nb, apply, bkp)

    print(f"Total remplacements: {total}")
    if total == 0:
        print("Aucun chemin détecté nécessitant modification.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Vérifie et corrige des chemins courants dans les notebooks')
    parser.add_argument('--apply', action='store_true', help='Applique les modifications. Sans ce flag, dry-run.')
    args = parser.parse_args()
    main(args.apply)
