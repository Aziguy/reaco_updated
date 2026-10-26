---
title: Données
description: Entretenir les prix, les métriques, la table Ciqual et les sauvegardes.
sidebar:
  order: 2
---

## Prix

`sync_prices` importe les relevés récents d'Open Prices et recalcule les recettes. En production, elle tourne chaque jour (voir [Tâches planifiées](/reaco_updated/deploiement/taches-planifiees/)).

```bash
uv run python manage.py sync_prices                 # tous les ingrédients chiffrables
uv run python manage.py sync_prices tomate beurre   # quelques ingrédients
uv run python manage.py sync_prices --days 90 --pages 5
uv run python manage.py sync_prices --skip-metrics  # sans recalcul des recettes
```

Un service indisponible pour un ingrédient est signalé sur la sortie d'erreur sans interrompre les autres.

### Contrôler la qualité des prix

- Dans l'administration, **Relevés de prix** : filtrez par ingrédient pour repérer des prix aberrants (produit transformé dans une catégorie large, unité mal interprétée).
- Sur la fiche d'une recette, la part de prix relevés et le détail par ingrédient montrent les ingrédients sans prix.
- Corrigez la catégorie Open Food Facts de l'ingrédient ou videz-la, puis relancez `sync_prices <slug>`. Les relevés déjà importés restent en base : supprimez-les dans l'administration si besoin.

Les relevés plus anciens que `PRICE_HISTORY_DAYS` sont ignorés par l'estimateur mais restent en base.

## Métriques des recettes

```bash
uv run python manage.py refresh_metrics
```

Recalcule coût, CO2 et valeurs nutritionnelles de toutes les recettes. Utile après une modification en masse des ingrédients, ou si l'API Impact CO2 était indisponible lors du dernier calcul (le CO2 reste alors vide).

## Table Ciqual

Les valeurs nutritionnelles viennent de la table Ciqual 2025 de l'Anses ([doi:10.57745/RDMHWY](https://doi.org/10.57745/RDMHWY), Licence Ouverte 2.0). Seuls les aliments utilisés par les ingrédients de démonstration sont copiés dans `demo/ciqual.json`.

À la publication d'une nouvelle table :

1. Téléchargez-la sur [ciqual.anses.fr](https://ciqual.anses.fr).
2. Pour chaque code présent dans `demo/ciqual.json`, mettez à jour `kcal`, `proteins`, `fat` et `carbs` (pour 100 g), et vérifiez que le code existe toujours. Mettez à jour la clé `source`.
3. Rechargez les ingrédients puis les métriques :

   ```bash
   uv run python manage.py seed_demo
   ```

4. Mettez à jour la mention « Ciqual 2025 » et le DOI dans `templates/core/about.html`, `templates/core/credits.html`, `templates/recipes/detail.html` et le README.

Sur une instance dont les ingrédients ont été modifiés dans l'administration, préférez une mise à jour manuelle dans l'administration : `seed_demo` réécrit les ingrédients de démonstration.

## Données de démonstration

`seed_demo` est idempotente : elle crée ou met à jour ingrédients, régimes et recettes à partir de `demo/recipes.json`, remplace leurs ingrédients et étapes, et ne réimporte une image que si elle a changé de nom (ou avec `--refresh-images`). Les recettes créées dans l'administration ne sont pas touchées.

## Sauvegardes

Voir [Mise en production](/reaco_updated/deploiement/mise-en-production/#sauvegardes). Les relevés de prix se reconstruisent avec `sync_prices` ; les données des utilisateurs (comptes, garde-manger, listes) et les recettes ajoutées dans l'administration, elles, n'existent que dans la base.
