---
title: Recettes et ingrédients
description: Ajouter un ingrédient chiffré, une recette de démonstration, une photo et ses crédits.
sidebar:
  order: 3
---

Deux voies : l'administration pour une instance donnée, ou `demo/recipes.json` pour enrichir les données de démonstration livrées avec le dépôt.

## Ajouter un ingrédient

Un ingrédient n'est utile que s'il est relié aux données ouvertes :

| Champ | Exemple | Sert à |
| --- | --- | --- |
| `off_category` | `en:tomatoes` | Prix Open Prices. Choisissez la catégorie la plus précise sur [la taxonomie Open Food Facts](https://world.openfoodfacts.org/categories). |
| `price_unit` | `kg`, `l` ou `unit` | Unité dans laquelle les prix sont comparés |
| `unit_weight_g` | `120` | Poids moyen d'une pièce : conversion entre pièces et kilos |
| `impactco2_slug` | `tomate` | Facteur carbone ADEME |
| `ciqual_code` et valeurs pour 100 g | `20276` | Valeurs nutritionnelles, relevées sur [ciqual.anses.fr](https://ciqual.anses.fr) |
| `aisle` | `produce` | Regroupement par rayon dans les listes de courses |
| `is_staple` | sel, poivre, huile | Ignoré dans les courses et les suggestions |

Puis lancez `uv run python manage.py sync_prices <slug>` pour importer ses prix et recalculer les recettes.

:::caution[Catégories trop larges]
Une catégorie large mélange produits bruts et transformés (une catégorie « tomates » contient aussi des sauces). L'estimateur privilégie les prix en vrac quand il y en a au moins 5, mais une catégorie précise reste le meilleur moyen d'avoir des prix justes. Contrôlez le résultat sur la fiche d'une recette qui utilise l'ingrédient, et laissez `off_category` vide plutôt que d'utiliser une catégorie trompeuse.
:::

## Ajouter une recette de démonstration

Les données de démonstration sont dans `demo/` :

| Fichier | Contenu |
| --- | --- |
| `recipes.json` | `diets`, `ingredients` et `recipes` |
| `ciqual.json` | Aliments Ciqual utilisés, indexés par code |
| `images/*.webp`, `images/*.svg` | Photos et illustrations |
| `images/credits.json` | Auteur, licence et source de chaque photo |

### Format d'une recette

```json
{
  "title": "Choucroute de poisson",
  "summary": "Une choucroute légère au saumon, prête en moins d'une heure.",
  "course": "main",
  "difficulty": 3,
  "servings": 2,
  "prep": 15,
  "cook": 40,
  "origin": "Normandie, France",
  "diets": ["Pescétarien", "Sans gluten"],
  "featured": true,
  "image": "choucroute-de-poisson.webp",
  "ingredients": [["Choucroute crue", 400, "g"], ["Pavé de saumon", 2, "piece"]],
  "steps": ["Rincez la choucroute à l'eau froide et égouttez-la."]
}
```

- `course` : `starter`, `main`, `salad`, `soup`, `dessert`, `breakfast`, `snack`, `sauce` ou `drink`.
- `difficulty` : 1 (très facile) à 4 (expert).
- `ingredients` : `[nom, quantité, unité]` ou `[nom, quantité, unité, précision]`. Le nom doit exister dans la liste `ingredients` du fichier ; unités possibles : `g`, `kg`, `ml`, `cl`, `l`, `piece`, `tbsp`, `tsp`, `pinch`.
- `diets` : noms présents dans la liste `diets`.

### Format d'un ingrédient

```json
{"name": "Pavé de saumon", "aisle": "fish", "price_unit": "kg", "unit_weight_g": 125,
 "off": "en:salmon-fillets", "co2": "saumon", "ciqual": "26036"}
```

`off`, `co2`, `ciqual`, `unit_weight_g` et `staple` sont facultatifs. Ajoutez l'aliment correspondant dans `demo/ciqual.json` (`kcal`, `proteins`, `fat`, `carbs` pour 100 g).

### Photo et crédits

1. Trouvez une photo sous licence libre (CC0, CC BY ou CC BY-SA), par exemple sur [Wikimedia Commons](https://commons.wikimedia.org).
2. Recadrez-la et convertissez-la en WebP de 1000 px de large au maximum, nommée comme le slug de la recette (`choucroute-de-poisson.webp`).
3. Ajoutez son crédit dans `demo/images/credits.json` :

   ```json
   "choucroute-de-poisson.webp": {
     "author": "Nom de l'auteur",
     "license": "CC BY-SA 4.0",
     "license_url": "https://creativecommons.org/licenses/by-sa/4.0",
     "source": "https://commons.wikimedia.org/wiki/File:..."
   }
   ```

Sans photo libre satisfaisante, une illustration SVG originale convient (exemple : `dahl-de-lentilles-corail.svg`) ; sans entrée dans `credits.json`, elle est créditée « Illustration Comégusto ». Les crédits s'affichent sous la photo et sur la page `/credits/`.

### Charger et vérifier

```bash
uv run python manage.py seed_demo                    # idempotent
uv run python manage.py seed_demo --refresh-images   # remplace aussi les images existantes
uv run python manage.py sync_prices                  # prix des nouveaux ingrédients
```

Vérifiez la fiche : quantités et unités (pluriels), coût, CO2, valeurs nutritionnelles (une couverture inférieure à 100 % signale un ingrédient sans données Ciqual ou sans conversion en grammes) et crédit de la photo.

## Dans l'administration

Les recettes se créent aussi dans l'administration, avec leurs ingrédients et étapes en ligne. À l'enregistrement, le coût, le CO2, les valeurs nutritionnelles et l'index de recherche sont recalculés.
