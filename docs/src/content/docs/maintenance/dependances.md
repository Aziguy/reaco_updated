---
title: Mises à jour
description: Mettre à jour Python, Django, les dépendances, htmx, Tailwind et les images Docker.
sidebar:
  order: 1
---

## Calendrier des versions majeures

| Composant | Version | Fin de support | À prévoir |
| --- | --- | --- | --- |
| Django | 5.2 LTS | avril 2028 | Passer à la LTS suivante (6.2, prévue en avril 2027) avant cette date |
| Python | 3.13 | octobre 2029 | Fixé dans `.python-version` et l'image `python:3.13-slim` |
| PostgreSQL | 17 | novembre 2029 | Image `postgres:17-alpine` ; une montée de version majeure demande un `pg_dump` et une restauration |
| Node.js (compilation des styles) | 22 | avril 2027 | Image `node:22-alpine` du `Dockerfile` |

Vérifiez les dates sur [la page des versions de Django](https://www.djangoproject.com/download/#supported-versions) et [endoflife.date](https://endoflife.date).

## Dépendances Python

Les contraintes sont dans `pyproject.toml`, les versions exactes dans `uv.lock`.

```bash
uv lock --upgrade-package django      # une dépendance
uv lock --upgrade                     # toutes, dans les limites de pyproject.toml
uv sync
uv run pytest && uv run python manage.py check --deploy
```

Django est contraint à `>=5.2,<5.3` : les correctifs de sécurité 5.2.x arrivent avec `uv lock --upgrade-package django`, le passage à une nouvelle version majeure se fait volontairement en modifiant la contrainte.

Avant une montée de version de Django, lisez les notes de version, lancez les tests avec les avertissements de dépréciation visibles (`uv run python -Wd -m pytest`) et vérifiez la compatibilité de django-allauth, django-csp, django-unfold, djangorestframework et drf-spectacular.

Après une mise à jour de django-unfold, ouvrez l'administration : de nouveaux textes peuvent apparaître en anglais. Ajoutez leur traduction dans `locale/fr/LC_MESSAGES/django.po`, puis compilez avec `uv run --with babel pybabel compile -d locale -D django -l fr`.

## Dépendances front-end

`package.json` fixe des versions exactes.

```bash
npm outdated
npm install --save-exact tailwindcss@<version> @tailwindcss/cli@<version>
npm run build
```

### htmx

htmx est vendorisé pour être servi par le site (CSP stricte, pas de CDN) :

```bash
npm install --save-exact htmx.org@<version>
npm run vendor       # copie dist/htmx.min.js vers static/vendor/htmx.min.js
```

Commitez `package.json`, `package-lock.json` et `static/vendor/htmx.min.js`, puis vérifiez les interactions (filtres, portions, garde-manger, courses).

## Outils et intégration continue

| Élément | Mise à jour |
| --- | --- |
| Hooks pre-commit | `uv run pre-commit autoupdate` |
| Actions GitHub | Versions majeures dans `.github/workflows/*.yml` |
| uv dans l'image | `COPY --from=ghcr.io/astral-sh/uv:0.9` du `Dockerfile` |
| Images Docker | `postgres`, `redis` dans `docker-compose.yml`, `caddy` dans `docker-compose.prod.yml` |
| Documentation | `docs/package.json` (Astro, Starlight), puis `npm install` dans `docs/` |

Dependabot n'est pas configuré : un fichier `.github/dependabot.yml` peut automatiser ces propositions de mise à jour.

## Après une mise à jour

1. `uv run pytest` et `uv run ruff check .`.
2. `npm run build`, puis vérification visuelle des pages principales en clair et en sombre.
3. `docker compose up -d --build` pour valider l'image.
4. Un commit par mise à jour significative (`Upgrade Django to 5.2.x`).
