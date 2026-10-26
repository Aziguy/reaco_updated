---
title: Visite du dépôt
description: Où se trouve quoi dans le dépôt Comégusto.
---

```text
config/                 réglages (settings.py, settings_test.py), URLs, WSGI/ASGI
apps/
  core/                 accueil, tableau de bord, saison, contact, santé, balises de templates
  accounts/             utilisateur (connexion par email), profil, localisation, suppression
  recipes/              ingrédients, recettes, unités, recherche, coût, CO2, nutrition
  integrations/         clients Open Food Facts, Open Prices, Impact CO2, géocodage IGN
  pricing/              magasins, relevés de prix, synchronisation, estimateur de panier
  pantry/               garde-manger, scan, statistiques, suggestions, rappels
  shopping/             listes de courses, fusion, déduction du stock, comparaison
  api/                  API REST (DRF) et schéma OpenAPI
  guide/                guide utilisateur intégré : chapitres, figures, commande de capture
  conftest.py           fixtures pytest partagées
templates/              gabarits Django, un dossier par application, partials/ pour les fragments
assets/app.css          source Tailwind CSS v4, compilée vers static/css/app.css
static/                 JavaScript (js/), htmx vendorisé (vendor/), logos et favicon (img/), captures du guide (img/guide/)
demo/                   recettes de démonstration, table Ciqual réduite, photos et crédits
docker/                 entrypoint.sh (migrations) et scheduler.sh (tâches quotidiennes)
deploy/Caddyfile        reverse proxy HTTPS de production
docs/                   cette documentation (Astro Starlight) et captures du README
.github/workflows/      CI, tâches planifiées, publication de la documentation
```

## Fichiers de configuration

| Fichier | Rôle |
| --- | --- |
| `pyproject.toml`, `uv.lock` | Dépendances Python, réglages pytest, coverage et ruff |
| `package.json`, `package-lock.json` | Tailwind CSS et htmx |
| `.env.example` | Modèle des variables d'environnement |
| `.pre-commit-config.yaml` | Vérifications avant commit (ruff, fins de ligne, clés privées, fichiers volumineux) |
| `Dockerfile` | Image multi-étapes : compilation des styles avec Node, puis image Python |
| `docker-compose.yml` | Pile de développement : PostgreSQL, Redis, web, scheduler |
| `docker-compose.prod.yml` | Surcouche de production avec Caddy |

## Organisation d'une application

Chaque application de `apps/` suit le même découpage :

| Fichier | Contenu |
| --- | --- |
| `models.py` | Modèles et QuerySets |
| `services.py` | Logique métier sans HTTP (pantry, shopping) |
| `views.py`, `urls.py`, `forms.py` | Pages et fragments HTMX |
| `admin.py` | Administration Django |
| `management/commands/` | Commandes de gestion |
| `tests/` | Tests pytest de l'application |

La logique métier vit dans des modules dédiés (`services.py`, `metrics.py`, `estimator.py`, `sync.py`) pour être réutilisée par les vues, l'API et les commandes.
