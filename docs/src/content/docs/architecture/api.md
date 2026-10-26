---
title: API REST
description: API REST de Comégusto avec Django REST Framework et drf-spectacular.
sidebar:
  order: 6
---

L'API est construite avec Django REST Framework (`apps/api/`). Le schéma OpenAPI est généré par drf-spectacular ; Swagger UI est servi localement (`drf-spectacular-sidecar`), sans CDN.

| URL | Contenu |
| --- | --- |
| `/api/docs/` | Documentation interactive (Swagger UI) |
| `/api/schema/` | Schéma OpenAPI 3 |
| `/api/v1/` | Racine de l'API navigable |

## Points d'accès

| Point d'accès | Méthodes | Accès |
| --- | --- | --- |
| `/api/v1/recipes/`, `/api/v1/recipes/{slug}/` | GET | public |
| `/api/v1/recipes/{slug}/estimate/?servings=&lat=&lon=&radius_km=` | GET | public |
| `/api/v1/ingredients/`, `/api/v1/ingredients/{slug}/` | GET | public |
| `/api/v1/pantry/` | GET, POST, PUT, PATCH, DELETE | authentifié, propre à l'utilisateur |
| `/api/v1/shopping-lists/` | GET, POST, PUT, PATCH, DELETE | authentifié |
| `/api/v1/shopping-lists/{id}/add-recipe/` | POST | authentifié |
| `/api/v1/shopping-items/{id}/` | PUT, PATCH, DELETE | authentifié |
| `/api/v1/products/{code-barres}/` | GET | authentifié |

- La liste des recettes accepte les mêmes paramètres que la page web (`q`, `course`, `diet`, `difficulty`, `max_minutes`, `sort`), grâce au même `RecipeFilterForm`.
- `estimate` limite `servings` entre 1 et 30 et `radius_km` à 100, puis applique `estimate_near()` : voir [Prix et métriques](/reaco_updated/architecture/prix-et-metriques/#recherche-géographique).
- `add-recipe` attend `recipe` (slug), `servings` et `use_pantry`, et réutilise `shopping.services.add_recipe`.
- `products` interroge Open Food Facts et renvoie 404 si le produit est inconnu ou si le service est indisponible.

## Authentification et permissions

- Session Django (navigateur) ou jeton : `Authorization: Token <clé>`. Les jetons se créent dans l'administration (`rest_framework.authtoken`).
- Permission par défaut : lecture publique, écriture authentifiée (`IsAuthenticatedOrReadOnly`).
- Les ressources personnelles héritent de `OwnedMixin` : le QuerySet est filtré sur `request.user` et `perform_create` rattache l'objet à l'utilisateur. Un utilisateur ne peut ni lire ni modifier les données d'un autre, ce que vérifient les tests de `apps/api/tests/`.

## Pagination et limites

- Pagination par numéro de page, 20 éléments par page (`?page=2`), avec `count`, `next` et `previous`.
- Limitation de débit : 60 requêtes par minute en anonyme, 240 par minute authentifié.

## Ajouter un point d'accès

1. Écrire le sérialiseur dans `apps/api/serializers.py`.
2. Écrire le ViewSet dans `apps/api/views.py`, en réutilisant les services métier plutôt qu'en dupliquant la logique. Pour une ressource personnelle, hériter de `OwnedMixin` et définir `model`.
3. Documenter les paramètres non déduits automatiquement avec `@extend_schema`.
4. Enregistrer le ViewSet dans le routeur de `apps/api/urls.py`.
5. Tester l'accès anonyme, l'accès authentifié et l'isolation entre utilisateurs.
