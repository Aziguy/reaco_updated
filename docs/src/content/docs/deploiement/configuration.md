---
title: Configuration
description: Emails, connexion Google, sécurité et référence de toutes les variables d'environnement.
sidebar:
  order: 7
---
Toute la configuration passe par des variables d'environnement : fichier `.env` à la racine ([serveur VPS](/reaco_updated/deploiement/serveur-vps/) avec Docker Compose) ou variables de la plateforme (PaaS). Après une modification, redémarrez l'application : `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d`.

## Emails

Comégusto envoie des emails pour :

| Usage | Destinataire |
| --- | --- |
| Vérification de l'adresse à l'inscription, réinitialisation du mot de passe | l'utilisateur |
| Rappels de produits bientôt périmés (tâche quotidienne) | l'utilisateur |
| Formulaire de contact | `CONTACT_EMAIL` |
| Erreurs serveur (500) | `ADMINS` |

Sans configuration, les emails sont affichés dans la console (`consolemail://`) : pratique en développement, inutile en production.

### 1. Choisir un fournisseur

| Fournisseur | Pour qui | Offre gratuite |
| --- | --- | --- |
| **Brevo** (recommandé) | Production, société française | 300 emails par jour, sans carte bancaire |
| **Boîte mail de votre nom de domaine** (OVHcloud, Gandi, Infomaniak...) | Vous avez déjà un domaine avec une messagerie | Incluse dans l'offre du domaine |
| **Gmail** | Tests et très petits volumes | Oui, mais expéditeur limité à l'adresse Gmail et risque de spam |
| Mailjet, Scaleway Transactional Email, Amazon SES, Postmark | Alternatives SMTP classiques | Selon le fournisseur |

### 2. Écrire `EMAIL_URL`

```ini
EMAIL_URL=smtp+tls://IDENTIFIANT:MOT_DE_PASSE@serveur:587
DEFAULT_FROM_EMAIL=Comégusto <bonjour@example.org>
CONTACT_EMAIL=contact@example.org
```

| Schéma | Port usuel | Chiffrement |
| --- | --- | --- |
| `smtp+tls://` | 587 (ou 2525) | STARTTLS |
| `smtp+ssl://` | 465 | SSL/TLS direct |
| `consolemail://` | | affichage dans la console |
| `dummymail://` | | aucun envoi |

> Les caractères spéciaux de l'identifiant et du mot de passe doivent être encodés : `@` devient `%40`, `/` devient `%2F`, `:` devient `%3A`, etc. Pour encoder une valeur :
>
> ```bash
> python3 -c "from urllib.parse import quote; print(quote(input('Valeur : '), safe=''))"
> ```

`DEFAULT_FROM_EMAIL` doit être une adresse autorisée par le fournisseur (expéditeur ou domaine validé), sinon les envois sont refusés.

### 3. Exemples

**Brevo**

1. Créez un compte sur [brevo.com](https://www.brevo.com).
2. Dans **Expéditeurs, domaines et IP dédiées**, ajoutez votre domaine (recommandé) ou au moins l'adresse d'expédition, puis validez-la.
3. Dans **SMTP et API**, onglet **SMTP**, relevez l'identifiant de connexion et générez une **clé SMTP** (pas une clé API).
4. Renseignez :

   ```ini
   EMAIL_URL=smtp+tls://IDENTIFIANT%40smtp-brevo.com:CLE_SMTP@smtp-relay.brevo.com:587
   DEFAULT_FROM_EMAIL=Comégusto <bonjour@example.org>
   ```

**Boîte mail OVHcloud** (les autres registrars fonctionnent de la même façon, avec leur propre serveur)

```ini
EMAIL_URL=smtp+ssl://bonjour%40example.org:MOT_DE_PASSE@ssl0.ovh.net:465
DEFAULT_FROM_EMAIL=Comégusto <bonjour@example.org>
```

**Gmail**

1. Activez la validation en deux étapes du compte Google.
2. Sur [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), créez un mot de passe d'application nommé « Comégusto ».
3. Copiez les 16 lettres sans les espaces :

   ```ini
   EMAIL_URL=smtp+tls://adresse%40gmail.com:MOTDEPASSEAPPLICATION@smtp.gmail.com:587
   DEFAULT_FROM_EMAIL=Comégusto <adresse@gmail.com>
   ```

Gmail remplace l'expéditeur par l'adresse du compte. Pour un site public, préférez un fournisseur avec votre propre domaine.

### 4. Améliorer la délivrabilité

Avec votre propre domaine, ajoutez dans sa zone DNS les enregistrements **SPF**, **DKIM** et **DMARC** indiqués par le fournisseur. Sans eux, une grande partie des emails arrive en spam.

### 5. Tester

```bash
docker compose exec web python manage.py sendtestemail vous@example.org
docker compose exec web python manage.py sendtestemail --admins
```

Sur un PaaS, lancez la même commande depuis le shell de la plateforme. Une fois l'envoi validé, imposez la vérification des adresses si l'inscription est ouverte au public :

```ini
ACCOUNT_EMAIL_VERIFICATION=mandatory
```

### 6. Dépannage

| Symptôme | Cause probable | Solution |
| --- | --- | --- |
| Erreur après une dizaine de secondes (`timed out`) | Port SMTP bloqué par l'hébergeur | Essayez le port 2525 (Brevo) ou changez d'offre. L'offre gratuite de Render bloque les ports 25, 465 et 587. |
| `535 Authentication failed` | Identifiant ou mot de passe faux, ou non encodé | Vérifiez la clé SMTP et l'encodage de `@` en `%40`. |
| `Sender not valid`, `550` | `DEFAULT_FROM_EMAIL` non validé chez le fournisseur | Validez l'adresse ou le domaine d'expédition. |
| Emails reçus en spam | Domaine non authentifié | Ajoutez SPF, DKIM et DMARC. |
| Rien n'est envoyé, aucune erreur | `EMAIL_URL` absent | Les emails partent dans la console : consultez les journaux. |

Le délai maximal d'une connexion SMTP est réglable avec `EMAIL_TIMEOUT` (10 secondes par défaut).

## Connexion avec Google

Facultative : le bouton « Google » apparaît sur la page de connexion dès que `GOOGLE_CLIENT_ID` est renseigné.

1. Sur [console.cloud.google.com](https://console.cloud.google.com), créez un projet (par exemple « Comégusto »).
2. Ouvrez **Google Auth Platform** :
   - **Branding** : nom de l'application, email d'assistance, logo facultatif, domaine autorisé (`example.org`) ;
   - **Audience** : type **Externe**, puis **Publier l'application** pour l'ouvrir à tous les comptes Google. Les seules données demandées (adresse email et profil) ne nécessitent pas de validation par Google.
3. Dans **Clients**, créez un client de type **Application Web** :
   - **Origines JavaScript autorisées** : `https://example.org` ;
   - **URI de redirection autorisés** : `https://example.org/compte/google/login/callback/`. Ajoutez `http://localhost:8000/compte/google/login/callback/` pour le développement.
4. Copiez l'identifiant et le secret dès la création : Google n'affiche plus le secret ensuite.

   ```ini
   GOOGLE_CLIENT_ID=1234567890-abc.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-...
   ```

5. Redémarrez l'application et testez depuis la page de connexion.

Une erreur `redirect_uri_mismatch` signifie que l'URI déclarée ne correspond pas exactement au domaine (protocole, sous-domaine et barre oblique finale compris).

## Domaine et sécurité

| Variable | Rôle |
| --- | --- |
| `ALLOWED_HOSTS` | Domaines servis, séparés par des virgules. Défini automatiquement à partir de `DOMAIN` avec `docker-compose.prod.yml`. |
| `CSRF_TRUSTED_ORIGINS` | Origines HTTPS de confiance (`https://example.org`). Automatique avec `docker-compose.prod.yml`. |
| `SECRET_KEY` | Clé unique et secrète : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`. La changer déconnecte tous les utilisateurs. |
| `ADMIN_URL` | Chemin de l'administration, à personnaliser (`gestion-8f3k/`). |
| `SECURE_SSL_REDIRECT`, `SECURE_COOKIES` | Redirection HTTPS et cookies sécurisés, actifs par défaut hors `DEBUG`. Ne les désactivez que derrière un proxy qui ne transmet pas `X-Forwarded-Proto`. |
| `SECURE_HSTS_SECONDS`, `SECURE_HSTS_PRELOAD` | HSTS d'un an par défaut. N'activez le préchargement qu'une fois tous les sous-domaines en HTTPS. |
| `MFA_REQUIRED_FOR_STAFF` | Double authentification obligatoire pour l'administration (`true` par défaut). |
| `SIGNUP_LIMIT_PER_IP` | Comptes créés au plus par adresse IP et par jour (5 par défaut, 0 pour désactiver). |
| `BLOCKED_EMAIL_DOMAINS` | Domaines refusés à l'inscription, en plus de la liste des adresses jetables (séparés par des virgules). |

Créez le premier administrateur avec `python manage.py createsuperuser`. À sa première visite de l'administration, il active la double authentification (application ou clé d'accès) : gardez ses codes de secours en lieu sûr.

## Base de données, cache et médias

| Variable | Rôle |
| --- | --- |
| `DATABASE_URL` | URL PostgreSQL : `postgres://utilisateur:motdepasse@hote:5432/base`. Ajoutez `?sslmode=require` pour une base distante (Neon, etc.). |
| `CONN_MAX_AGE` | Durée de vie des connexions en secondes (60 par défaut, 0 avec un pooler en mode transaction). |
| `REDIS_URL` | Cache partagé entre les processus (`redis://redis:6379/0`). Sans Redis, chaque processus a son propre cache. |
| `MEDIA_ROOT`, `SERVE_MEDIA` | Dossier des médias et service par Django. Avec Caddy, `SERVE_MEDIA=false` est déjà défini. |
| `AWS_*` | Stockage S3 des médias, voir [Stockage des médias](/reaco_updated/deploiement/stockage-medias/). |

## Données ouvertes et prix

| Variable | Rôle |
| --- | --- |
| `PRICE_COUNTRIES` | Pays des magasins pris en compte (`FR`, ou `FR,BE`). |
| `PRICE_HISTORY_DAYS` | Ancienneté maximale des prix importés (365 par défaut). |
| `IMPACT_CO2_API_KEY` | Facultative : l'API Impact CO2 de l'ADEME fonctionne sans clé, une clé (demandée sur [impactco2.fr](https://impactco2.fr)) identifie vos appels. |
| `INTEGRATIONS_TIMEOUT` | Délai maximal des appels aux services ouverts, en secondes (8 par défaut). |

`CONTACT_EMAIL` figure aussi dans l'en-tête `User-Agent` envoyé à Open Food Facts, comme le demande le projet.

## Assistant IA

L'assistant fonctionne avec un ou plusieurs fournisseurs, configurés dans l'administration (section **Assistant IA**). Les clés restent dans l'environnement. Sans clé, l'application fonctionne normalement et l'assistant utilise ses replis sans IA. Voir [Assistant IA](/reaco_updated/architecture/assistant-ia/).

| Variable | Rôle |
| --- | --- |
| `ANTHROPIC_API_KEY` | Clé de l'API Anthropic (console.anthropic.com). Fixez aussi une limite de dépenses dans la console. |
| `GITHUB_MODELS_TOKEN` | Facultatif : jeton GitHub avec la permission `models:read`, pour GitHub Models. |
| `MISTRAL_API_KEY` | Facultatif : clé Mistral, modèle de secours hébergé dans l'Union européenne. |
| `AI_MONTHLY_BUDGET_USD` | Plafond de dépenses mensuel de l'application, en dollars (20 par défaut). |
| `AI_ENABLED` | `false` coupe l'assistant (`true` par défaut). |
| `AI_TIMEOUT` | Délai maximal d'un appel, en secondes (60 par défaut). |

Après le premier déploiement, vérifiez dans l'administration que les fournisseurs voulus sont actifs et que la colonne **clé présente** est cochée.

## Abonnements

Formules, coordonnées de virement et Wero se règlent dans l'administration (section **Abonnements**). Stripe reste désactivé tant que ses clés manquent. Voir [Abonnements et paiements](/reaco_updated/architecture/abonnements/).

| Variable | Rôle |
| --- | --- |
| `STRIPE_SECRET_KEY` | Facultatif : clé secrète Stripe (`sk_live_…` ou `sk_test_…`). |
| `STRIPE_WEBHOOK_SECRET` | Facultatif : secret de signature du webhook (`whsec_…`). |
| `BILLING_USD_TO_EUR` | Taux de conversion du coût de l'IA sur la page « Où va votre argent » (0,86 par défaut). |

## Tâches planifiées

| Variable | Rôle |
| --- | --- |
| `SITE_URL` | Adresse publique utilisée dans les liens des emails de rappel. Automatique avec `docker-compose.prod.yml`. |
| `SCHEDULER_INTERVAL` | Intervalle du service `scheduler`, en secondes (86 400 par défaut, soit une fois par jour). |
| `SYNC_PAGES` | Nombre de pages Open Prices lues par ingrédient à chaque synchronisation (2 par défaut). |
| `RUN_MIGRATIONS` | `1` (défaut) applique les migrations au démarrage du conteneur web. |

Sans service `scheduler`, voir [Tâches planifiées](/reaco_updated/deploiement/taches-planifiees/).

## Journaux et alertes

| Variable | Rôle |
| --- | --- |
| `LOG_LEVEL` | `INFO` par défaut, `DEBUG` pour diagnostiquer, `WARNING` pour alléger. |
| `ADMINS` | Adresses qui reçoivent le détail des erreurs serveur, séparées par des virgules. Nécessite un `EMAIL_URL` fonctionnel. |

## Référence des variables

| Variable | Défaut | Section |
| --- | --- | --- |
| `DEBUG` | `false` | Développement uniquement |
| `SECRET_KEY` | obligatoire hors `DEBUG` | [Sécurité](#domaine-et-sécurité) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | [Sécurité](#domaine-et-sécurité) |
| `CSRF_TRUSTED_ORIGINS` | vide | [Sécurité](#domaine-et-sécurité) |
| `ADMIN_URL` | `admin/` | [Sécurité](#domaine-et-sécurité) |
| `SECURE_SSL_REDIRECT`, `SECURE_COOKIES` | actifs hors `DEBUG` | [Sécurité](#domaine-et-sécurité) |
| `SECURE_HSTS_SECONDS`, `SECURE_HSTS_PRELOAD` | `31536000`, `false` | [Sécurité](#domaine-et-sécurité) |
| `MFA_REQUIRED_FOR_STAFF` | `true` | [Sécurité](#domaine-et-sécurité) |
| `SIGNUP_LIMIT_PER_IP`, `BLOCKED_EMAIL_DOMAINS` | `5`, vide | [Sécurité](#domaine-et-sécurité) |
| `DATABASE_URL` | SQLite local | [Base de données](#base-de-données-cache-et-médias) |
| `CONN_MAX_AGE` | `60` | [Base de données](#base-de-données-cache-et-médias) |
| `REDIS_URL` | vide | [Cache](#base-de-données-cache-et-médias) |
| `MEDIA_ROOT`, `SERVE_MEDIA` | `media/`, `true` | [Médias](#base-de-données-cache-et-médias) |
| `AWS_STORAGE_BUCKET_NAME` et `AWS_*` | vide | [Médias](/reaco_updated/deploiement/stockage-medias/) |
| `EMAIL_URL` | `consolemail://` | [Emails](#emails) |
| `EMAIL_TIMEOUT` | `10` | [Emails](#6-dépannage) |
| `DEFAULT_FROM_EMAIL` | `Comégusto <CONTACT_EMAIL>` | [Emails](#2-écrire-email_url) |
| `CONTACT_EMAIL` | `contact@comegusto.local` | [Emails](#emails) |
| `ACCOUNT_EMAIL_VERIFICATION` | `optional` | [Emails](#5-tester) |
| `ADMINS` | vide | [Alertes](#journaux-et-alertes) |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | vide | [Google](#connexion-avec-google) |
| `PRICE_COUNTRIES` | `FR` | [Prix](#données-ouvertes-et-prix) |
| `PRICE_HISTORY_DAYS` | `365` | [Prix](#données-ouvertes-et-prix) |
| `IMPACT_CO2_API_KEY` | vide | [Données ouvertes](#données-ouvertes-et-prix) |
| `INTEGRATIONS_TIMEOUT` | `8` | [Données ouvertes](#données-ouvertes-et-prix) |
| `ANTHROPIC_API_KEY`, `GITHUB_MODELS_TOKEN`, `MISTRAL_API_KEY` | vide | [Assistant IA](#assistant-ia) |
| `AI_MONTHLY_BUDGET_USD`, `AI_ENABLED`, `AI_TIMEOUT` | `20`, `true`, `60` | [Assistant IA](#assistant-ia) |
| `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` | vide | [Abonnements](#abonnements) |
| `BILLING_USD_TO_EUR` | `0.86` | [Abonnements](#abonnements) |
| `SITE_URL`, `SCHEDULER_INTERVAL`, `SYNC_PAGES`, `RUN_MIGRATIONS` | voir la section | [Tâches](#tâches-planifiées) |
| `LOG_LEVEL` | `INFO` | [Journaux](#journaux-et-alertes) |
| `DOMAIN`, `POSTGRES_PASSWORD` | vide | `docker-compose.prod.yml`, voir [Serveur VPS](/reaco_updated/deploiement/serveur-vps/) |
