# Contribuer à Comégusto

Merci de votre intérêt ! Voici comment proposer une modification.

## Préparer l'environnement

```bash
uv sync
npm install && npm run build
uv run pre-commit install
cp .env.example .env
uv run python manage.py migrate && uv run python manage.py seed_demo
```

## Règles

- Une branche par sujet, partant de `master`, et une pull request liée à une issue.
- Des commits courts et précis, à l'impératif, en anglais (`Add pantry expiry reminders`).
- Du code lisible plutôt que commenté : un commentaire explique un « pourquoi », jamais un « quoi ».
- Toute nouvelle logique métier est accompagnée de tests. Les appels réseau sont simulés avec `respx`.
- `uv run ruff check .`, `uv run ruff format --check .` et `uv run pytest` doivent passer, y compris sur PostgreSQL (`DATABASE_URL=postgres://... uv run pytest`), comme dans la CI.
- Interface : pas de script ni de style en ligne (la CSP les bloque), classes Tailwind dans les templates, interactions avec HTMX.

## Ajouter un ingrédient ou une recette

Ingrédients et recettes se gèrent dans l'administration. Pour qu'un ingrédient soit chiffré, renseignez sa catégorie Open Food Facts (par exemple `en:carrots`, à vérifier sur <https://world.openfoodfacts.org/categories>) son identifiant ADEME Impact CO2 et son code Ciqual avec les valeurs pour 100 g (énergie, protéines, lipides, glucides) relevées sur <https://ciqual.anses.fr>. Lancez ensuite `sync_prices <slug>`.

Pour une recette de démonstration (`demo/recipes.json`), utilisez une image sous licence libre (CC0, CC BY, CC BY-SA, par exemple sur Wikimedia Commons), redimensionnée en WebP de 1000 px de large maximum, et ajoutez son auteur, sa licence et sa source dans `demo/images/credits.json`. Sans photo libre satisfaisante, une illustration SVG originale convient aussi.

## Données ouvertes

Comégusto vit grâce aux contributions de la communauté. Le meilleur moyen d'améliorer les prix est de photographier vos tickets et étiquettes sur [Open Prices](https://prices.openfoodfacts.org).
