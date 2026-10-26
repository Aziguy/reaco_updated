---
title: Tâches planifiées
description: Synchronisation quotidienne des prix et rappels de péremption.
sidebar:
  order: 5
---

Deux commandes doivent tourner chaque jour :

| Commande | Rôle |
| --- | --- |
| `sync_prices --pages 2` | Importe les nouveaux prix Open Prices puis recalcule les recettes |
| `send_expiry_reminders --base-url https://DOMAIN` | Envoie un email aux utilisateurs dont des produits périment dans les 2 jours |

| Hébergement | Solution |
| --- | --- |
| Docker Compose ([serveur VPS](/reaco_updated/deploiement/serveur-vps/)) | Le service `scheduler` (`docker/scheduler.sh`) enchaîne les rappels puis la synchronisation, puis attend `SCHEDULER_INTERVAL` secondes (86 400 par défaut). |
| PaaS avec cron | Planifiez les deux commandes chaque jour. |
| PaaS sans cron gratuit | Le workflow `.github/workflows/scheduled.yml` exécute ces commandes chaque nuit à 4 h 30 UTC depuis GitHub Actions. |

## Workflow GitHub Actions

Ajoutez dans **Settings > Secrets and variables > Actions** du dépôt :

| Secret | Obligatoire | Rôle |
| --- | --- | --- |
| `DATABASE_URL` | oui | Base de production, accessible depuis internet |
| `SECRET_KEY` | oui | Même valeur qu'en production |
| `EMAIL_URL` | pour les rappels | Sans lui, seuls les prix sont synchronisés |
| `SITE_URL` | recommandé | Adresse publique utilisée dans les liens des emails |

Sans `DATABASE_URL`, le workflow ne fait rien. Il peut aussi être lancé à la main depuis l'onglet **Actions** (`workflow_dispatch`).
