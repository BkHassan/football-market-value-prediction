# Projet_MarketValue_Player

Résumé
- Projet d'analyse et de modélisation de la valeur de marché des joueurs.

Structure recommandée
- `data/raw/` : fichiers CSV bruts (scraping)
- `data/processed/` : fichiers résultants (fusion, agrégations)
- `notebooks/` : notebooks Jupyter pour exploration et visualisation
- `src/` : scripts et modules réutilisables
- `models/` : modèles sérialisés (ex. `.pkl`)

Commandes utiles
1. Réorganiser la structure du projet (déplace les CSVs et notebooks) :
```bash
python scripts/reorganize_project.py --apply
```

2. Installer les dépendances :
```bash
pip install -r requirements.txt
```

Notes
- Le script de réorganisation crée une sauvegarde `backup_<timestamp>/` avant de déplacer les fichiers.
- Vérifiez les notebooks après réorganisation pour ajuster d'éventuels chemins relatifs.
