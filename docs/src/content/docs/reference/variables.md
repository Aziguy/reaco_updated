---
title: Variables d'environnement
description: Où trouver la liste complète des variables d'environnement.
sidebar:
  order: 2
---

La liste complète des variables, avec leur valeur par défaut, est dans [Configuration : référence des variables](/reaco_updated/deploiement/configuration/#référence-des-variables). Le fichier `.env.example` à la racine du dépôt sert de modèle.

Variables essentielles en production :

| Variable | Rôle |
| --- | --- |
| `SECRET_KEY` | Clé secrète Django |
| `DOMAIN` ou `ALLOWED_HOSTS` + `CSRF_TRUSTED_ORIGINS` | Domaines servis |
| `DATABASE_URL` (ou `POSTGRES_PASSWORD` avec Docker Compose) | Base PostgreSQL |
| `EMAIL_URL`, `DEFAULT_FROM_EMAIL`, `CONTACT_EMAIL` | Envoi d'emails |
| `ADMIN_URL` | Chemin de l'administration |
