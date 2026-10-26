---
title: Plateforme PaaS
description: Déployer Comégusto sur Render, Railway, Clever Cloud, Scalingo, Koyeb ou Cloud Run.
sidebar:
  order: 3
---

Le principe est le même sur Render, Railway, Clever Cloud, Scalingo, Koyeb ou Cloud Run : la plateforme construit l'image à partir du `Dockerfile` et l'exécute.

1. **Base de données** : créez un PostgreSQL (celui de la plateforme ou Neon) et récupérez son URL de connexion.
2. **Médias** : sur la plupart des PaaS, le disque est effacé à chaque déploiement. Configurez un [stockage S3](/reaco_updated/deploiement/stockage-medias/).
3. **Service web** : créez un service à partir du dépôt GitHub, de type Docker, port `8000`, chemin de vérification de santé `/health/`.
4. **Variables d'environnement** :

   | Variable | Valeur |
   | --- | --- |
   | `SECRET_KEY` | chaîne aléatoire longue |
   | `ALLOWED_HOSTS` | `comegusto.onrender.com,comegusto.example.org` |
   | `CSRF_TRUSTED_ORIGINS` | `https://comegusto.example.org` |
   | `DATABASE_URL` | URL PostgreSQL (ajoutez `?sslmode=require` pour Neon) |
   | `AWS_*` | voir [Stockage des médias](/reaco_updated/deploiement/stockage-medias/) |
   | `EMAIL_URL`, `DEFAULT_FROM_EMAIL`, `CONTACT_EMAIL` | votre SMTP, voir [Configurer les emails](/reaco_updated/deploiement/configuration/#emails) |
   | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | facultatif, voir [Connexion avec Google](/reaco_updated/deploiement/configuration/#connexion-avec-google) |
   | `REDIS_URL` | facultatif |

5. **Premier lancement** : depuis le shell de la plateforme, exécutez `python manage.py createsuperuser`, `seed_demo` puis `sync_prices`. Sans shell disponible, lancez ces commandes depuis votre poste avec la même `DATABASE_URL`.
6. **Tâches quotidiennes** : utilisez les tâches cron de la plateforme si elles existent, sinon le [workflow GitHub fourni](/reaco_updated/deploiement/taches-planifiees/).

## Particularités

- **Render gratuit** : mise en veille après 15 minutes d'inactivité et ports SMTP 25, 465 et 587 bloqués. Essayez le port 2525 de Brevo ou passez à une instance payante.
- **Clever Cloud et Scalingo** : choisissez le déploiement Docker et ajoutez l'extension PostgreSQL ; l'URL de la base est fournie dans une variable que vous recopiez dans `DATABASE_URL`.
- **Cloud Run** : l'image se construit avec Cloud Build ou depuis GitHub. Définissez le port `8000` et une instance minimale à `0` pour rester dans le quota gratuit.
