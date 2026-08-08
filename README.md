# Projet_MarketValue_Player

Analyse et modélisation de la valeur de marché des joueurs (SofaScore), avec stockage PostgreSQL via Docker.

## Pourquoi PostgreSQL + Docker ?

Les CSV restent utiles pour l’exploration. PostgreSQL apporte :
- un schéma typé (contraintes, index),
- des requêtes SQL reproductibles,
- une base locale identique pour tout le monde grâce à Docker.

On garde volontairement une architecture simple (pas d’Airflow, Kafka, dbt, etc.) : adaptée à un projet étudiant / portfolio.

## Structure du projet

```text
.
├── .env.example              # modèle de credentials (à copier vers .env)
├── docker-compose.yml        # PostgreSQL 16
├── db/
│   └── init/
│       └── 01_schema.sql     # schéma créé au premier démarrage Docker
├── data/
│   ├── raw/                  # CSV sources (scraping / fusion)
│   └── processed/            # dataset_final.csv pour les notebooks
├── notebooks/                # exploration / visualisation / ML
├── src/
│   ├── etl.py                # ancien ETL CSV -> CSV
│   └── load_to_postgres.py   # ETL CSV -> PostgreSQL (+ refresh CSV)
├── models/                   # modèles sérialisés
└── requirements.txt
```

## Schéma de base (3 tables)

| Table | Rôle | Source |
|---|---|---|
| `players` | identité + valeur de marché | `sofascore_database_globale.csv` |
| `player_stats` | stats de performance | `sofascore_top5leagues_players_stat.csv` |
| `players_ml` | table plate pour le ML | jointure des deux sources |

Les noms de colonnes SQL sont en `snake_case` anglais pour rester lisibles. Le mapping depuis les en-têtes CSV (ex. `Buts` → `goals`) est fait dans le script Python.

## Mise en route

### 1) Prérequis

- Python 3.10+
- Docker Desktop (avec Docker Compose)

### 2) Credentials (fichier `.env`)

```bash
cp .env.example .env
```

Pourquoi un `.env` ?
- les mots de passe ne sont pas dans le code,
- Docker Compose et le script Python lisent les mêmes variables,
- `.env` est ignoré par Git.

### 3) Installer les dépendances Python

```bash
pip install -r requirements.txt
```

### 4) Démarrer PostgreSQL

```bash
docker compose up -d
```

Au premier démarrage, Postgres exécute automatiquement `db/init/01_schema.sql`
(dossier monté dans `/docker-entrypoint-initdb.d`).

Vérifier que le conteneur est prêt :

```bash
docker compose ps
```

### 5) Charger les CSV dans PostgreSQL

```bash
python src/load_to_postgres.py
```

Ce script :
1. lit `data/raw/sofascore_database_globale.csv` et `data/raw/sofascore_top5leagues_players_stat.csv`,
2. nettoie les types (`jersey_number` avec `-`, `market_value`, etc.),
3. fusionne les joueurs et les stats pour `players_ml`,
4. charge les 3 tables (TRUNCATE puis INSERT),
5. met à jour `data/processed/dataset_final.csv` pour les notebooks.

### 6) Vérifier les données (optionnel)

```bash
docker compose exec db psql -U marketvalue -d marketvalue -c "SELECT COUNT(*) FROM players_ml;"
docker compose exec db psql -U marketvalue -d marketvalue -c "SELECT name, market_value, goals FROM players_ml ORDER BY market_value DESC NULLS LAST LIMIT 5;"
```

## Commandes utiles

Arrêter la base (données conservées dans le volume Docker) :

```bash
docker compose down
```

Recréer la base depuis zéro (⚠️ supprime les données du volume) :

```bash
docker compose down -v
docker compose up -d
python src/load_to_postgres.py
```

ETL CSV-only (sans base) :

```bash
python src/etl.py
```

## Choix techniques (et pourquoi)

- **PostgreSQL 16** : version stable et courante en entreprise.
- **Docker Compose** : environnement reproductible en une commande.
- **SQL init script** : le schéma est versionné et lisible.
- **SQLAlchemy + psycopg2 + pandas** : stack simple pour un ETL pédagogique.
- **3 tables** : assez structurées pour montrer un modèle relationnel, sans sur-ingénierie.
