---
title: Feuille de route
description: Pistes d'évolution de Comégusto.
sidebar:
  order: 1
---

Le suivi se fait dans les [issues GitHub](https://github.com/Aziguy/reaco_updated/issues). Chaque piste ci-dessous devient une issue avec une liste de tâches avant d'être développée.

## Pistes

| Piste | Intérêt | Points d'attention |
| --- | --- | --- |
| Contribution de prix vers Open Prices depuis l'application | Enrichir la base commune, surtout localement | Authentification Open Food Facts de l'utilisateur, envoi de preuves (photo du ticket) |
| Import de recettes | Élargir le catalogue | Licences des recettes et des photos, correspondance des ingrédients |
| Planning de repas hebdomadaire | Courses de la semaine en un clic, moins de gaspillage | Réutiliser `shopping.services.add_recipe` et les suggestions du garde-manger |
| Notifications push | Rappels de péremption sans email | Web Push et service worker, compatibles avec la CSP |
| Application installable (PWA) | Usage mobile, scan en magasin | Manifeste, service worker, mode hors ligne limité |

## Idées techniques

- Recherche plein texte PostgreSQL si le catalogue dépasse quelques milliers de recettes (l'index actuel `search_text` reste portable entre SQLite et PostgreSQL).
- Dependabot pour les mises à jour de dépendances.
- Tests de bout en bout dans la CI (Playwright) sur les parcours principaux.

Pour ajouter une source de données, suivez [Ajouter une source de données](/reaco_updated/evolution/nouvelle-source/) ; pour une décision structurante, ajoutez une entrée aux [décisions d'architecture](/reaco_updated/evolution/decisions/).
