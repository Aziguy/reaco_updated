---
title: Choisir un hébergeur
description: Ce qu'il faut à Comégusto et comparatif des hébergeurs gratuits et payants.
sidebar:
  order: 1
---

Trois façons de mettre Comégusto en ligne, du gratuit au payant. Toutes reposent sur la même image Docker et les mêmes variables d'environnement, détaillées dans [Configuration](/reaco_updated/deploiement/configuration/) (emails, connexion Google, sécurité...).

## Ce qu'il faut à Comégusto

| Brique | Rôle | Obligatoire |
| --- | --- | --- |
| Application (image Docker, Gunicorn) | Pages, API, administration | oui |
| PostgreSQL | Données | oui (SQLite seulement pour tester) |
| Stockage persistant des médias | Photos des recettes ajoutées dans l'administration | oui, disque ou S3 |
| Accès internet sortant | Open Prices, Open Food Facts, ADEME, IGN | oui |
| Tâche quotidienne | Synchronisation des prix, rappels de péremption | recommandé |
| Redis | Cache partagé entre plusieurs processus | facultatif |
| SMTP | Emails (vérification, rappels, contact) | recommandé |

Une petite instance suffit : 512 Mo de RAM pour l'application, et une base de quelques dizaines de Mo pour les recettes et les prix.

## Quel hébergeur choisir ?

:::note
Offres relevées en octobre 2026. Les conditions des offres gratuites changent souvent : vérifiez-les sur le site de l'hébergeur avant de vous engager.
:::

### Gratuit

| Combinaison | Pour qui | Points d'attention |
| --- | --- | --- |
| **Oracle Cloud Always Free** (VM Arm) + [serveur VPS](/reaco_updated/deploiement/serveur-vps/) | La solution gratuite la plus complète : tout tourne sur la VM, y compris PostgreSQL et le planificateur | Création de compte avec carte bancaire, capacité Arm parfois indisponible selon la région. L'allocation Always Free varie selon les sources (jusqu'à 4 cœurs et 24 Go, ou moins) : vérifiez la page officielle. |
| **Render** (web gratuit) + **Neon** (PostgreSQL gratuit) + **Cloudflare R2** (médias) + GitHub Actions (tâches) | Démonstration, petit trafic | L'instance gratuite Render se met en veille après 15 minutes sans visite (réveil d'environ une minute), 750 h par mois, ports SMTP bloqués. Le PostgreSQL gratuit de Render expire après 30 jours, d'où Neon (0,5 Go et 100 heures de calcul par mois sur l'offre gratuite). |
| **Google Cloud Run** + Neon + R2 + GitHub Actions | Démonstration avec un quota gratuit généreux | Compte de facturation Google obligatoire ; quota mensuel gratuit (180 000 vCPU-secondes, 2 millions de requêtes en facturation à la requête). |

À éviter : **PythonAnywhere gratuit**. L'accès internet sortant y est limité à une liste blanche, ce qui empêche d'interroger les services ouverts.

### Payant

| Hébergeur | Type | Prix indicatif | Pourquoi |
| --- | --- | --- | --- |
| **Hetzner Cloud**, **OVHcloud VPS**, **Scaleway Instances** | VPS + [serveur VPS](/reaco_updated/deploiement/serveur-vps/) | Environ 4 à 10 € par mois | Meilleur rapport qualité-prix, contrôle total, hébergement en Europe. Hetzner a revu ses prix en 2026 et certaines gammes économiques ne sont plus toujours disponibles. |
| **Clever Cloud** | PaaS français | À l'usage, facturation à la seconde (calculateur sur le site) | Déploiement Docker, PostgreSQL managé avec sauvegardes quotidiennes, hébergement en France. |
| **Scalingo** | PaaS français | PostgreSQL Starter à partir de 7,20 € HT par mois, essai gratuit de 30 jours | Simple, hébergement en France, option SecNumCloud. |
| **Railway** | PaaS | Offre Hobby à 5 $ par mois, incluant 5 $ de consommation | Très simple, déjà utilisé par l'ancienne version du projet. |
| **Render** (instances payantes) | PaaS | À partir de quelques dollars par mois | Supprime la mise en veille et les limites de l'offre gratuite. |
| **Koyeb** | PaaS | Offre Pro à 29 $ par mois, incluant 10 $ de consommation | Racheté par Mistral AI en 2026, le service continue. |

**Notre recommandation** : un petit VPS européen avec Docker Compose et Caddy (environ 5 € par mois, tout compris). Pour un projet de démonstration sans budget : Oracle Cloud Always Free avec la même méthode, ou Render + Neon + R2.

## Sources des offres

- Render : [offre gratuite](https://render.com/docs/free)
- Koyeb : [FAQ tarifaire](https://www.koyeb.com/docs/faqs/pricing)
- Railway : [offres](https://docs.railway.com/pricing/plans)
- Neon : [tarifs](https://neon.com/pricing)
- Google Cloud Run : [tarifs](https://cloud.google.com/run/pricing)
- Oracle Cloud : [Always Free](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm)
- Cloudflare R2 : [tarifs](https://developers.cloudflare.com/r2/pricing/)
- Clever Cloud : [tarifs](https://www.clever.cloud/pricing)
- Scalingo : [PostgreSQL](https://scalingo.com/databases/postgresql)
- Hetzner : [hausse de prix de juin 2026](https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do)
- PythonAnywhere : [fonctionnalités des comptes gratuits](https://help.pythonanywhere.com/pages/FreeAccountsFeatures/)
