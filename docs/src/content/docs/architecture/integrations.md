---
title: Intégrations de données ouvertes
description: Client HTTP commun, cache, pannes et services ouverts utilisés par Comégusto.
sidebar:
  order: 3
---

Tous les services externes passent par `apps/integrations/`. Chaque module expose des fonctions simples qui renvoient des `dataclass` immuables, jamais du JSON brut.

| Service | Module | Usage | Cache | Licence |
| --- | --- | --- | --- | --- |
| [Open Prices](https://prices.openfoodfacts.org) | `openprices.py` | Relevés de prix par catégorie, produit ou zone | 6 h | ODbL |
| [Open Food Facts](https://world.openfoodfacts.org) | `openfoodfacts.py` | Fiche produit à partir d'un code-barres | 24 h | ODbL |
| [ADEME Impact CO2](https://impactco2.fr) | `impactco2.py` | Empreinte carbone des aliments, fruits et légumes de saison | 7 jours | Licence Ouverte 2.0 |
| [IGN Géoplateforme](https://geoservices.ign.fr) | `geocoding.py` | Géocodage d'un code postal ou d'une ville | 30 jours | Licence Ouverte 2.0 |
| [Anses Ciqual 2025](https://ciqual.anses.fr) | `demo/ciqual.json` | Valeurs nutritionnelles pour 100 g | fichier local | Licence Ouverte 2.0 |

## Client HTTP commun

`apps/integrations/http.py` définit `JsonClient`, construit avec une URL de base, des en-têtes facultatifs et une durée de cache.

```python
from apps.integrations.http import JsonClient, ServiceError

client = JsonClient("https://example.org/api", cache_ttl=3600)
data = client.get("/items", {"q": "tomate"})   # dict, list ou None (404)
```

Comportement de `get()` :

1. **Cache des réponses** : la clé est un hash SHA-256 de l'URL de base, du chemin et des paramètres. Une réponse en cache est renvoyée sans appel réseau.
2. **Cache des pannes** : si le même appel a échoué il y a moins de 5 minutes (`FAILURE_TTL`), `ServiceError` est levée immédiatement. Une page ne reste donc jamais bloquée par un service indisponible.
3. **Nouvelles tentatives** : sur erreur réseau ou statut 429, 500, 502, 503, 504, le client réessaie `INTEGRATIONS["RETRIES"]` fois (2 par défaut) avec une attente exponentielle à partir de `BACKOFF` (0,5 s), plafonnée à 2 s.
4. **Réponses** : un 404 renvoie `None`, une autre erreur HTTP ou un JSON invalide lève `ServiceError`.

Chaque requête porte un délai maximal (`INTEGRATIONS_TIMEOUT`, 8 s par défaut) et un `User-Agent` identifiable, `Comegusto/2.0 (CONTACT_EMAIL)`, comme le demande Open Food Facts.

:::tip[Règle pour les appelants]
Une vue ou une commande qui appelle un service ouvert doit attraper `ServiceError` et afficher un état dégradé. Des fonctions `safe_*` existent pour les cas courants, par exemple `impactco2.safe_food_footprints()` qui renvoie `{}` en cas de panne.
:::

En tests, les appels sont interceptés par `respx` : voir [Tests et qualité](/reaco_updated/developpement/tests/).

## Open Prices

`openprices.fetch_prices()` interroge `/api/v1/prices` par pages de 100, triées du plus récent au plus ancien, avec ces filtres facultatifs :

| Paramètre | Filtre Open Prices | Usage |
| --- | --- | --- |
| `category_tag` | `category_tag` | Prix en vrac d'une catégorie (`en:tomatoes`) |
| `product_category` | `product__categories_tags__contains` | Produits emballés d'une catégorie |
| `product_code` | `product_code` | Un produit précis (scan) |
| `since` | `date__gte` | Profondeur d'historique |
| `near` | `lat`, `lon`, `radius_km` | Recherche géographique |

`normalize()` ramène chaque prix à une unité de base : directement si Open Prices indique `price_per` (`KILOGRAM`, `LITER`, `UNIT`), sinon à partir de la contenance du produit (g, kg, mg, ml, cl, l). Les magasins sont lus dans `location` quand il s'agit d'un lieu OpenStreetMap.

La synchronisation et l'estimation sont décrites dans [Prix et métriques](/reaco_updated/architecture/prix-et-metriques/).

## Open Food Facts

`openfoodfacts.get_product(code)` vérifie le format du code-barres (8 à 14 chiffres), appelle `/api/v2/product/{code}` en limitant les champs demandés, et renvoie un `Product` (nom français de préférence, marque, contenance, image, Nutri-Score, Green-Score, NOVA, catégories).

Dans le garde-manger, `pantry.services.lookup_barcode()` complète le formulaire : ingrédient le plus spécifique correspondant aux catégories du produit, quantité, et valeur estimée par la médiane des prix Open Prices du produit sur un an, hors promotions.

## ADEME Impact CO2

- `seasonal_produce(month)` : fruits et légumes de saison (`/fruitsetlegumes`), utilisés par la page Saison et le badge « de saison ».
- `food_footprints()` : facteurs en kg CO2e par kg d'aliment, issus de `/fruitsetlegumes` et de `/alimentation?category=group`, indexés par identifiant ADEME (`Ingredient.impactco2_slug`).

L'API fonctionne sans clé. Si `IMPACT_CO2_API_KEY` est défini, il est envoyé en en-tête `Authorization: Bearer`.

## IGN Géoplateforme

`geocoding.geocode_city(query)` interroge `/geocodage/search` (type `municipality`, un résultat) et renvoie libellé, ville, code postal et coordonnées. Il est appelé à l'enregistrement du profil quand l'utilisateur saisit un code postal ou une ville.

## Anses Ciqual

Pas d'appel réseau : `demo/ciqual.json` contient les aliments Ciqual 2025 utilisés par les ingrédients de démonstration (code, nom, kcal, protéines, lipides, glucides pour 100 g). `seed_demo` recopie ces valeurs sur chaque `Ingredient` ; elles restent modifiables dans l'administration. Voir [Mettre à jour Ciqual](/reaco_updated/maintenance/donnees/#table-ciqual).
