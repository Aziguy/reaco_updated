---
title: Commandes de gestion
description: Commandes manage.py propres à Comégusto et commandes Django utiles.
sidebar:
  order: 1
---

Toutes les commandes se lancent avec `uv run python manage.py <commande>` en local, ou `docker compose exec web python manage.py <commande>` avec Docker.

## Commandes du projet

### `seed_demo`

Charge les ingrédients, régimes et recettes de démonstration de `demo/` (idempotent), avec photos, crédits et valeurs Ciqual, puis calcule les métriques.

| Option | Effet |
| --- | --- |
| `--refresh-images` | Remplace aussi les images déjà importées |

### `sync_prices [slug ...]`

Importe les relevés Open Prices des ingrédients qui ont une catégorie Open Food Facts, puis recalcule les recettes.

| Option | Défaut | Effet |
| --- | --- | --- |
| `slug ...` | tous | Limite la synchronisation à ces ingrédients |
| `--days N` | `PRICE_HISTORY_DAYS` | Profondeur d'historique en jours |
| `--pages N` | 3 | Pages de 100 prix par requête |
| `--skip-metrics` | | Ne recalcule pas les recettes |

### `refresh_metrics`

Recalcule coût par portion, empreinte carbone et valeurs nutritionnelles de toutes les recettes.

### `send_expiry_reminders`

Envoie un email récapitulatif aux utilisateurs actifs, ayant gardé les rappels activés, dont des produits périment bientôt.

| Option | Défaut | Effet |
| --- | --- | --- |
| `--days N` | 2 | Produits qui périment dans les N prochains jours (ou déjà périmés) |
| `--base-url URL` | `http://localhost:8000` | Adresse du site dans le lien de l'email |

### `capture_guide [nom ...]`

Régénère les captures annotées du guide utilisateur dans `static/img/guide/`, en thème clair et sombre. Nécessite le serveur de développement lancé sur la même base. Voir [Guide utilisateur intégré](/reaco_updated/developpement/guide-utilisateur/).

| Option | Défaut | Effet |
| --- | --- | --- |
| `nom ...` | toutes | Limite la capture à ces figures |
| `--base-url URL` | `http://127.0.0.1:8000` | Adresse du serveur à capturer |

## Commandes Django utiles

| Commande | Usage |
| --- | --- |
| `createsuperuser` | Créer un administrateur (connexion par email) |
| `changepassword <email>` | Changer le mot de passe d'un utilisateur |
| `sendtestemail <email>`, `sendtestemail --admins` | Tester la configuration SMTP |
| `check --deploy` | Vérifier les réglages de sécurité de production |
| `makemigrations --name <nom>` | Créer une migration nommée |
| `migrate` | Appliquer les migrations (automatique au démarrage du conteneur web) |
| `collectstatic` | Rassembler les fichiers statiques (fait lors de la construction de l'image) |
| `shell` | Console Python avec les modèles chargés |
