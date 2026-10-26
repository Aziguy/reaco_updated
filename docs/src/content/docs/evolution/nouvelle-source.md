---
title: Ajouter une source de données
description: Intégrer un nouveau service de données ouvertes pas à pas.
sidebar:
  order: 2
---

Exemple : une API ouverte qui fournit un indicateur par aliment.

## 1. Vérifier la source

- Licence compatible avec une réutilisation publique (Licence Ouverte, ODbL, CC BY...) et obligations d'attribution.
- Conditions d'usage : limites de débit, clé obligatoire, `User-Agent` demandé.
- Stabilité : API versionnée, documentation, historique de disponibilité.

## 2. Déclarer la configuration

Dans `config/settings.py`, ajoutez l'URL (et la clé éventuelle, lue dans l'environnement) au dictionnaire `INTEGRATIONS` :

```python
INTEGRATIONS = {
    # ...
    "EXAMPLE_URL": "https://api.example.org/v1",
    "EXAMPLE_API_KEY": env("EXAMPLE_API_KEY", default=""),
}
```

Documentez toute nouvelle variable dans `.env.example` et dans [Configuration](/reaco_updated/deploiement/configuration/#référence-des-variables).

## 3. Écrire le client

Créez `apps/integrations/example.py` sur le modèle des clients existants : un `JsonClient` avec une durée de cache adaptée au rythme de mise à jour de la source, et des `dataclass` immuables en sortie.

```python
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from .http import JsonClient, ServiceError

DAY = 24 * 3600


@dataclass(frozen=True)
class Indicator:
    slug: str
    value: Decimal


def _client() -> JsonClient:
    conf = settings.INTEGRATIONS
    headers = {"Authorization": f"Bearer {conf['EXAMPLE_API_KEY']}"} if conf["EXAMPLE_API_KEY"] else {}
    return JsonClient(conf["EXAMPLE_URL"], headers=headers, cache_ttl=7 * DAY)


def indicators() -> dict[str, Decimal]:
    data = _client().get("/indicators") or {}
    return {item["slug"]: Decimal(str(item["value"])) for item in data.get("items", [])}


def safe_indicators() -> dict[str, Decimal]:
    try:
        return indicators()
    except ServiceError:
        return {}
```

Le client commun gère déjà délai maximal, nouvelles tentatives, cache et mémorisation des pannes : voir [Intégrations](/reaco_updated/architecture/integrations/#client-http-commun).

## 4. Relier aux modèles

- Si la donnée dépend d'un ingrédient, ajoutez un identifiant sur `Ingredient` (comme `impactco2_slug`) et une migration, puis renseignez-le dans `demo/recipes.json` et `seed_demo`.
- Si la donnée doit être affichée dans les listes ou servir aux filtres, stockez une valeur précalculée sur `Recipe` et calculez-la dans `apps/recipes/metrics.py`, plutôt que d'appeler le service à l'affichage.

## 5. Afficher et dégrader proprement

- Si la source est indisponible, la page s'affiche sans la donnée, avec un message discret si besoin.
- Pour des images externes, ajoutez le domaine à `img-src` de la CSP dans `config/settings.py`.
- Ajoutez l'attribution dans les pages À propos et Crédits, et dans le tableau des données ouvertes du README.

## 6. Tester

- Tests du client avec `respx` : réponse normale, champs manquants, panne (500), introuvable (404).
- Tests du calcul ou de la vue qui l'utilise, avec la source simulée.
- Aucun appel réseau réel dans les tests.

## 7. Documenter

Mettez à jour [Intégrations](/reaco_updated/architecture/integrations/) et, si la source change l'architecture, ajoutez une [décision d'architecture](/reaco_updated/evolution/decisions/).
