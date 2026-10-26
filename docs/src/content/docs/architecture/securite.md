---
title: Sécurité
description: Mesures de sécurité de Comégusto et règles à respecter en développement.
sidebar:
  order: 7
---

## Secrets et configuration

- Aucun secret dans le code : tout passe par les variables d'environnement (`django-environ`). Hors `DEBUG`, l'application refuse de démarrer sans `SECRET_KEY`.
- `.env` est ignoré par git ; `.env.example` ne contient que des valeurs d'exemple.
- Le dépôt a Secret scanning et Push protection activés sur GitHub, et le hook pre-commit `detect-private-key` bloque les clés privées.

## HTTP

| Mesure | Réglage |
| --- | --- |
| Redirection HTTPS | `SECURE_SSL_REDIRECT`, actif hors `DEBUG`, avec `SECURE_PROXY_SSL_HEADER` pour les proxys |
| HSTS | Un an hors `DEBUG`, sous-domaines inclus, préchargement facultatif (`SECURE_HSTS_PRELOAD`) |
| Cookies | `Secure` hors `DEBUG`, `HttpOnly` pour la session |
| Clickjacking | `X-Frame-Options: DENY` et CSP `frame-ancestors 'none'` |
| Referrer | `strict-origin-when-cross-origin` |
| Isolation de fenêtre | `Cross-Origin-Opener-Policy: same-origin` |

Le contrôle `/health/` est traité par un middleware placé avant la validation de l'hôte et la redirection HTTPS, pour que les sondes des conteneurs fonctionnent en HTTP interne.

## Content Security Policy

`django-csp` applique une politique stricte : `default-src 'self'`, scripts et styles du site uniquement, `object-src 'none'`, `base-uri 'self'`. Les règles qui en découlent pour les templates sont détaillées dans [Front-end](/reaco_updated/architecture/front-end/#contraintes-de-la-csp).

## Authentification

- django-allauth, connexion par email, vérification de l'adresse réglable (`ACCOUNT_EMAIL_VERIFICATION`, `mandatory` recommandé en production), limitation de débit intégrée d'allauth.
- Validateurs de mots de passe Django (similarité, longueur, mots de passe courants, numérique).
- Connexion Google facultative, activée seulement si `GOOGLE_CLIENT_ID` est défini.
- Chemin de l'administration personnalisable (`ADMIN_URL`).

## Données personnelles

- Chaque vue et chaque point d'API qui touche au garde-manger, aux listes ou aux favoris filtre sur l'utilisateur connecté ; les tests vérifient qu'un autre utilisateur obtient une 404.
- L'utilisateur peut supprimer son compte et toutes ses données depuis son profil (confirmation par saisie).
- Les seules données envoyées à des tiers sont un code postal ou une ville (IGN) et un code-barres (Open Food Facts, Open Prices).

## Abus

- Formulaire de contact : pot de miel et limite de 3 messages par heure et par adresse IP (`apps/core/ratelimit.py`, compteur en cache).
- API : 60 requêtes par minute en anonyme, 240 authentifié.
- Téléversements limités à 5 Mo.

:::caution
Le compteur de limitation utilise le cache. Avec plusieurs processus Gunicorn, configurez `REDIS_URL` pour que la limite soit partagée.
:::

## Signaler une vulnérabilité

Écrivez à l'adresse de contact du projet plutôt que d'ouvrir une issue publique.
