---
title: Conventions
description: Règles de code, de commits, d'issues et de pull requests du projet Comégusto.
sidebar:
  order: 1
---

## Flux de travail

1. Chaque sujet a une issue GitHub, mise à jour au fil de l'implémentation (liste de tâches cochée).
2. Une branche par sujet, partant de `master`.
3. Plusieurs petits commits plutôt qu'un seul gros.
4. Une pull request liée à l'issue (`Closes #12`). La CI doit être verte.

## Commits

- En anglais, à l'impératif, courts et précis : `Add pantry expiry reminders`, `Fix Google sign-in missing dependencies (#20)`.
- Un commit = une intention. Le numéro d'issue entre parenthèses quand il y en a une.
- Pas de corps de message verbeux : le pourquoi détaillé va dans l'issue ou la pull request.

## Code Python

- Ruff pour le lint et le formatage (100 caractères par ligne, règles `E`, `F`, `W`, `I`, `B`, `UP`, `DJ`, `S`, `SIM`, `RUF`). `uv run pre-commit install` les lance avant chaque commit.
- Code lisible plutôt que commenté : un commentaire explique un « pourquoi », jamais un « quoi ». Docstrings d'une ligne pour les fonctions dont le rôle n'est pas évident.
- Logique métier dans des modules dédiés (`services.py`, `metrics.py`, `estimator.py`), pas dans les vues ni les templates.
- Appels aux services ouverts uniquement via `apps/integrations/`, avec gestion de `ServiceError`.
- Textes visibles en français, identifiants et noms de code en anglais.
- Annotations de type sur les fonctions métier, comme dans le code existant (`Decimal | None`, `list[Line]`).

## Templates et front-end

- Classes Tailwind dans les templates ; composants réutilisés (boutons, cartes, badges) déclarés en `@utility` dans `assets/app.css`.
- Aucun script ni style en ligne (bloqués par la CSP). Interactions avec HTMX, comportements dans `static/js/app.js` via `data-*`.
- Fragments HTMX préfixés par `_` (`_results.html`).
- Toute image a un `alt` ; tout bouton qui ouvre un panneau a `aria-expanded` et `aria-controls`.

## Rédaction

- Documentation, interface et issues en français, concises.
- Pas de tiret cadratin : utilisez deux-points, virgules ou parenthèses.

## Migrations

- Des migrations nommées selon leur contenu (`0004_recipe_search_text`), générées avec `makemigrations --name`.
- Une donnée à remplir pour les lignes existantes passe par `RunPython` dans la même migration (exemple : `apps/recipes/migrations/0004_recipe_search_text.py`).
- La CI échoue s'il manque une migration (`makemigrations --check`).
