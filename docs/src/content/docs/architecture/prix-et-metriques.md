---
title: Prix et métriques
description: Synchronisation des prix, estimateur de panier, coût, CO2 et valeurs nutritionnelles des recettes.
sidebar:
  order: 4
---

## Synchronisation des prix

`apps/pricing/sync.py`, appelé par la commande `sync_prices` :

1. Pour chaque ingrédient doté d'une catégorie Open Food Facts (`off_category`), `sync_ingredient()` récupère les relevés en vrac de cette catégorie sur `PRICE_HISTORY_DAYS` jours (365 par défaut).
2. S'il y a moins de 5 prix exploitables (`MIN_RAW_OBSERVATIONS`), il récupère aussi les prix des produits emballés de la catégorie, ramenés au kilo ou au litre grâce à leur contenance.
3. `store_records()` écarte les prix sans prix unitaire et ceux des magasins hors de `PRICE_COUNTRIES`, crée ou met à jour les magasins (`Store`, enseigne normalisée par `normalize_brand()` : « E. Leclerc », « Centre commercial E.Leclerc » et « E.Leclerc » sont fusionnées, de même que « ALDI » et « Aldi ») et les relevés (`PriceObservation`, clé `source_id`), le tout dans une transaction.
4. La commande recalcule ensuite les métriques de toutes les recettes, sauf avec `--skip-metrics`.

Relancer la commande est sans risque : les relevés déjà connus sont mis à jour, jamais dupliqués.

## Estimateur de panier

`apps/pricing/estimator.py` chiffre une liste de lignes `Line(ingredient, quantity, unit)`, issue d'une recette (`recipes.metrics.basket_lines`) ou d'une liste de courses (`shopping.services.basket_lines`).

1. Il lit les relevés hors promotion de la période, et convertit chaque prix dans l'unité de prix de l'ingrédient (`convert_unit_price`).
2. Quand un ingrédient a au moins 5 prix en vrac, les prix de produits emballés sont ignorés : les catégories larges contiennent aussi des produits transformés.
3. Le prix de référence d'un ingrédient est la **médiane** de ses relevés, après élimination des prix incohérents : `plausible()` écarte tout prix plus de 4 fois supérieur ou inférieur à la médiane (`MAX_PRICE_RATIO`), par exemple une tête d'ail vendue à l'unité convertie avec le poids d'une gousse. La quantité de la ligne est convertie dans l'unité de prix (`to_base`) pour obtenir le coût.
4. Pour chaque enseigne, l'estimateur prend la médiane des relevés plausibles de cette enseigne, comparés au prix de référence ; un ingrédient sans relevé dans l'enseigne est compté au prix médian global. Une enseigne n'est proposée que si au moins 40 % des ingrédients y ont un vrai relevé (`MIN_BRAND_COVERAGE`).
5. Les offres sont triées du total le plus bas au plus haut. Chaque offre indique la part de prix réellement relevés (`coverage`) et jusqu'à trois magasins.

### Recherche géographique

`estimate(lines, near=(latitude, longitude, radius_km))` ne garde, pour les offres par enseigne, que les magasins situés dans le rayon (distance haversine). `estimate_near()` revient à une estimation nationale si aucune enseigne proche n'est exploitable, et indique si la comparaison locale a été conservée. La position vient du profil de l'utilisateur (`User.location`) ou des paramètres `lat`, `lon` et `radius_km` de l'API.

## Métriques des recettes

`apps/recipes/metrics.py` calcule et enregistre sur `Recipe` :

| Métrique | Calcul |
| --- | --- |
| `cost_per_serving`, `price_coverage` | Total de l'estimateur divisé par le nombre de portions, et part des ingrédients chiffrés |
| `co2_per_serving` | Somme des quantités en kg multipliées par le facteur ADEME de l'ingrédient, divisée par les portions |
| `kcal`, `proteins_g`, `fat_g`, `carbs_g`, `nutrition_coverage` | Somme des valeurs Ciqual pour 100 g rapportées à la quantité, divisée par les portions, et part des ingrédients couverts |

Les quantités sont converties en kg par `units.to_kilograms()` : unités de masse, densité 1 pour les volumes et les cuillères (soupe 15 g, café 5 g, pincée 0,5 g), poids moyen pour les pièces (`unit_weight_g`). Une ligne sans quantité ou sans conversion possible est ignorée et fait baisser la couverture.

`refresh(recipe)` est appelé :

- par `sync_prices` et `refresh_metrics` pour toutes les recettes ;
- par `seed_demo` pour chaque recette chargée ;
- par l'administration après l'enregistrement d'une recette et de ses ingrédients (`RecipeAdmin.save_related`).

Ces valeurs sont donc lues directement en base par les listes et les filtres, sans calcul à l'affichage.

## Garde-manger et courses

- **Suggestions anti-gaspi** (`pantry.services.suggest_recipes`) : les recettes sont classées selon les ingrédients du garde-manger qu'elles utilisent, ceux qui périment sous 3 jours comptant triple. Les produits de base sont ignorés.
- **Statistiques** (`pantry.services.stats_for`) : produits consommés et jetés sur 30 jours, taux anti-gaspi et valeurs correspondantes.
- **Ajout d'une recette à une liste** (`shopping.services.add_recipe`) : quantités adaptées aux portions, produits de base ignorés, stock du garde-manger déduit quand les unités sont convertibles, fusion avec les articles existants de même ingrédient et même unité, pièces arrondies à l'unité supérieure.
