---
title: Mise en production
description: Sauvegardes, supervision et checklist de mise en production.
sidebar:
  order: 6
---

## Sauvegardes

- **Base de données (Docker Compose)** : une sauvegarde quotidienne par cron sur l'hôte, à copier hors du serveur :

  ```bash
  docker compose exec -T db pg_dump -U comegusto comegusto | gzip > backup-$(date +%F).sql.gz
  ```

  Restauration : `gunzip -c backup.sql.gz | docker compose exec -T db psql -U comegusto comegusto`.
- **Médias (Docker Compose)** : sauvegardez le volume Docker `media`.
- **PaaS** : activez les sauvegardes de la base proposées par la plateforme (souvent absentes des offres gratuites).

Testez régulièrement une restauration sur une base vide.

## Supervision

- `/health/` renvoie `{"status": "ok"}` quand l'application et la base répondent. Branchez-y un service de surveillance (UptimeRobot, Better Stack, ou celui de la plateforme).
- Renseignez `ADMINS` pour recevoir le détail des erreurs serveur par email.
- Journaux : `docker compose logs -f web scheduler`. Voir [Exploitation](/reaco_updated/maintenance/exploitation/).

## Checklist

- [ ] `DEBUG=false` et `SECRET_KEY` unique, jamais commitée.
- [ ] `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` limités à vos domaines.
- [ ] HTTPS actif (Caddy ou plateforme), `SECURE_SSL_REDIRECT` et cookies sécurisés laissés à leur valeur par défaut.
- [ ] `ADMIN_URL` personnalisée et mot de passe administrateur robuste.
- [ ] SMTP configuré et testé (`sendtestemail`), `ACCOUNT_EMAIL_VERIFICATION=mandatory` si l'inscription est ouverte au public.
- [ ] `ADMINS` renseigné pour recevoir les erreurs serveur.
- [ ] Médias persistants (volume ou S3) et sauvegardes de la base.
- [ ] `python manage.py check --deploy` sans avertissement.
- [ ] Tâche quotidienne de synchronisation des prix en place.
