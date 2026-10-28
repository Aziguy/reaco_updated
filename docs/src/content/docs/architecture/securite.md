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

**Exception : l'administration.** Le thème Unfold s'appuie sur Alpine.js et des attributs `style`. Sous `ADMIN_URL` seulement, `apps.core.middleware.CSPMiddleware` ajoute `'unsafe-eval'` aux scripts et `'unsafe-inline'` aux styles. Le reste du site garde la politique stricte, ce que vérifie un test. L'administration n'est accessible qu'au personnel connecté ; gardez un `ADMIN_URL` difficile à deviner en production.

## Authentification

- django-allauth, connexion par email, vérification de l'adresse réglable (`ACCOUNT_EMAIL_VERIFICATION`, `mandatory` recommandé en production), limitation de débit intégrée d'allauth.
- Validateurs de mots de passe Django (similarité, longueur, mots de passe courants, numérique).
- Connexion Google facultative, activée seulement si `GOOGLE_CLIENT_ID` est défini.
- Chemin de l'administration personnalisable (`ADMIN_URL`).

## Double authentification

`allauth.mfa` ajoute un second facteur à la connexion, quel que soit le moyen de connexion :

| Méthode | Détail |
| --- | --- |
| Application d'authentification | Codes TOTP à 6 chiffres (Google Authenticator, Microsoft Authenticator, 1Password…), secret chiffré en base |
| Clés d'accès | WebAuthn (empreinte, visage, Windows Hello, clé de sécurité) ; une clé « sans mot de passe » permet aussi de se connecter seule (`MFA_PASSKEY_LOGIN_ENABLED`) |
| Codes de secours | Dix codes à usage unique, créés à l'activation |

- Activer ou retirer une méthode redemande le mot de passe, et exige une adresse email vérifiée.
- Après le code, l'utilisateur peut faire confiance au navigateur pendant 14 jours (`MFA_TRUST_ENABLED`, cookie signé).
- Les écrans sont ceux du site (`templates/mfa/`) ; la page **Sécurité du compte** est `/compte/2fa/`.

**Administration.** La page de connexion de l'administration redirige vers celle du site (`secure_admin_login`), qui applique la double authentification. `apps.accounts.middleware.StaffMFAMiddleware` renvoie tout compte de l'équipe sans méthode active vers la page de sécurité (`MFA_REQUIRED_FOR_STAFF`, actif par défaut). Un super-utilisateur peut réinitialiser la double authentification d'un compte depuis la liste des utilisateurs, pour une personne qui a perdu son téléphone et ses codes.

:::note
Les jetons d'API (`TokenAuthentication`) ne passent pas par la double authentification : ils ne sont créés que par l'équipe, depuis l'administration. Traitez-les comme des mots de passe.
:::

## Données personnelles

- Chaque vue et chaque point d'API qui touche au garde-manger, aux listes ou aux favoris filtre sur l'utilisateur connecté ; les tests vérifient qu'un autre utilisateur obtient une 404.
- L'utilisateur peut supprimer son compte et toutes ses données depuis son profil (confirmation par saisie).
- Les seules données envoyées à des tiers sont un code postal ou une ville (IGN) et un code-barres (Open Food Facts, Open Prices).

## Paiements

- Aucune donnée de carte ne transite par Comégusto : Stripe Checkout et le portail client sont hébergés par Stripe.
- Le webhook Stripe est exempté de CSRF mais vérifie la signature (`STRIPE_WEBHOOK_SECRET`) ; il répond 404 tant que Stripe n'est pas configuré.
- Les clés Stripe restent dans l'environnement. L'IBAN et l'identifiant Wero, destinés à être affichés aux abonnés, sont en base.
- Une page de paiement n'est visible que par son abonné ; une formule n'est activée que par l'équipe (virement, Wero) ou par un événement signé (Stripe).

## Abus

### Comptes multiples

Créer plusieurs comptes pour cumuler les quotas gratuits de l'assistant est freiné, sans empreinte du navigateur ni donnée tierce :

| Mesure | Détail |
| --- | --- |
| Adresses jetables refusées | Liste `disposable-email-domains` (près de 10 000 domaines, sous-domaines compris), complétée par `BLOCKED_EMAIL_DOMAINS` |
| Une boîte mail, un compte | `User.email_canonical` : minuscules, sans `+étiquette`, sans les points de Gmail (`googlemail.com` compris) ; vérifié à l'inscription |
| Inscriptions par connexion | Au plus `SIGNUP_LIMIT_PER_IP` comptes créés par adresse IP et par jour (5 par défaut, 0 pour désactiver) |
| Email vérifié pour l'assistant | Un compte dont l'adresse attend sa confirmation n'utilise pas l'assistant |
| Jeton d'appareil | Cookie signé `cg_device` (HttpOnly, 2 ans), posé pour les comptes connectés uniquement ; seule son empreinte SHA-256 est en base (`Device`, `DeviceLink`) |
| Quota partagé | Les comptes gratuits vus sur un même appareil partagent le quota du jour de l'assistant ; abonnés et équipe gardent le leur |

Les comptes liés à un même appareil sont visibles sur la fiche utilisateur de l'administration (filtre **appareil partagé**). Ces mesures relèvent de la sécurité du service : le jeton n'est ni publicitaire ni partagé, mais il doit figurer dans la politique de confidentialité.

### Limites de débit

- Formulaire de contact : pot de miel et limite de 3 messages par heure et par adresse IP (`apps/core/ratelimit.py`, compteur en cache).
- API : 60 requêtes par minute en anonyme, 240 authentifié.
- Téléversements limités à 5 Mo.

:::caution
Le compteur de limitation utilise le cache. Avec plusieurs processus Gunicorn, configurez `REDIS_URL` pour que la limite soit partagée.
:::

## Signaler une vulnérabilité

Écrivez à l'adresse de contact du projet plutôt que d'ouvrir une issue publique.
