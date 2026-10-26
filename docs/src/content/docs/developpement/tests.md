---
title: Tests et qualité
description: Lancer et écrire les tests pytest, simuler les services ouverts et comprendre la CI.
sidebar:
  order: 2
---

## Lancer les tests

```bash
uv run pytest                     # SQLite en mémoire
uv run pytest --cov               # avec couverture
uv run pytest apps/pricing -k estimate
DATABASE_URL=postgres://comegusto:comegusto@localhost:5432/comegusto uv run pytest
```

Les tests utilisent `config/settings_test.py` (déclaré dans `pyproject.toml`) :

- base SQLite en mémoire, sauf si `DATABASE_URL` est défini ;
- hachage MD5 des mots de passe pour la vitesse, emails en mémoire (`django.core.mail.outbox`) ;
- cache en mémoire locale, limitation de débit de l'API désactivée ;
- une seule tentative et aucune attente pour les appels aux services ouverts.

Les tests doivent passer sur SQLite **et** PostgreSQL : la CI les lance sur PostgreSQL 17.

## Fixtures partagées

`apps/conftest.py` fournit :

| Fixture | Contenu |
| --- | --- |
| `_isolation` (automatique) | Vide le cache, isole `MEDIA_ROOT` dans un dossier temporaire et active `respx` |
| `http` | Le routeur `respx` pour déclarer des réponses simulées |
| `user`, `other_user`, `auth_client` | Utilisateurs de test et client connecté |
| `ingredients`, `recipe` | Tomate, œuf, lait, sel et une omelette de deux portions |
| `stores`, `prices` | Deux enseignes et quatre relevés de prix |

## Simuler un service ouvert

Aucun test n'appelle internet. Tout appel non simulé reçoit une réponse vide de `respx`, ce qui évite les fuites réseau sans faire échouer les tests qui ne s'intéressent pas à ce service.

```python
PRICES_URL = "https://prices.openfoodfacts.org/api/v1/prices"


def test_fetch_prices(http):
    route = http.get(PRICES_URL).respond(json={"items": [price_item()], "pages": 1})
    records = openprices.fetch_prices(category_tag="en:butters")
    assert route.called
    assert records[0].unit_price == Decimal("12.960")
```

Pour une panne : `.respond(500)` ou `.mock(side_effect=httpx.ConnectError)`.

## Que tester ?

- Toute nouvelle logique métier (estimateur, conversions, services) par des tests unitaires.
- Les vues : statut, contexte, fragment HTMX (`HTTP_HX_REQUEST="true"`).
- L'isolation des données : un autre utilisateur doit obtenir une 404.
- Les cas dégradés : service indisponible, paramètres invalides, données manquantes.

## Lint et formatage

```bash
uv run ruff check .          # --fix pour corriger
uv run ruff format .
uv run pre-commit run --all-files
```

## Intégration continue

`.github/workflows/ci.yml`, à chaque push sur `master` et sur les pull requests :

| Job | Étapes |
| --- | --- |
| `lint` | `ruff check` et `ruff format --check` |
| `test` | PostgreSQL 17, `makemigrations --check`, `pytest --cov` |
| `deploy-check` | `manage.py check --deploy --fail-level WARNING` avec une configuration de production |
| `docker` | Construction de l'image (après `lint` et `test`), avec cache GitHub Actions |

`.github/workflows/docs.yml` construit et publie cette documentation sur GitHub Pages quand `docs/` change.

## Vérification dans un navigateur

Avant une modification visible, vérifiez les pages concernées en largeur bureau et mobile, en thème clair et sombre, et la console du navigateur (une violation de CSP y apparaît).
