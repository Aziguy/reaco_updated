---
title: Installation
description: Installer Comégusto en local avec uv et npm, ou avec Docker Compose.
---

Deux façons de lancer le projet : directement sur votre poste (recommandé pour développer) ou avec Docker Compose (pile complète avec PostgreSQL et Redis).

## En local

### Prérequis

- [uv](https://docs.astral.sh/uv/) : il installe aussi Python 3.13 (version fixée dans `.python-version`).
- Node.js 20 ou plus, uniquement pour compiler les styles Tailwind.
- PostgreSQL est facultatif : sans `DATABASE_URL`, une base SQLite `db.sqlite3` est créée à la racine.

### Étapes

```bash
git clone https://github.com/Aziguy/reaco_updated.git comegusto && cd comegusto
uv sync                     # dépendances Python dans .venv
npm install && npm run build
cp .env.example .env        # DEBUG=true pour le développement
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py sync_prices
uv run python manage.py createsuperuser
uv run python manage.py runserver
```

- L'application répond sur <http://localhost:8000>, l'administration sur `/admin/` (chemin réglable avec `ADMIN_URL`) et la documentation de l'API sur `/api/docs/`.
- `seed_demo` charge 83 ingrédients et 31 recettes avec leurs photos. La commande est idempotente.
- `sync_prices` interroge Open Prices pour chaque ingrédient. Elle prend quelques minutes ; `sync_prices tomate oeuf` limite la synchronisation à quelques ingrédients.
- Les emails sont affichés dans la console (`EMAIL_URL=consolemail://`).

### Styles

```bash
npm run dev     # recompile static/css/app.css à chaque modification
```

`static/css/app.css` est généré et ignoré par git. Pensez à le recompiler après avoir ajouté des classes Tailwind dans un template.

### Vérifications avant commit

```bash
uv run pre-commit install   # une fois
uv run ruff check . && uv run ruff format --check .
uv run pytest
```

Voir [Tests et qualité](/reaco_updated/developpement/tests/).

## Avec Docker Compose

```bash
cp .env.example .env
docker compose up -d --build
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py sync_prices
docker compose exec web python manage.py createsuperuser
```

`docker-compose.yml` lance quatre services :

| Service | Rôle |
| --- | --- |
| `db` | PostgreSQL 17 (volume `pgdata`) |
| `redis` | Cache partagé |
| `web` | Gunicorn sur le port 8000, migrations appliquées au démarrage |
| `scheduler` | Boucle quotidienne : rappels de péremption puis synchronisation des prix |

Les médias sont stockés dans le volume `media`, partagé entre `web` et `scheduler`. Pour la production, voir [Serveur VPS](/reaco_updated/deploiement/serveur-vps/).

## Et ensuite ?

- [Visite du dépôt](/reaco_updated/demarrer/visite/) pour savoir où se trouve quoi.
- [Vue d'ensemble de l'architecture](/reaco_updated/architecture/vue-ensemble/).
