# Déployer Comégusto

Ce guide couvre trois façons de mettre Comégusto en ligne, du gratuit au payant. Toutes reposent sur la même image Docker et les mêmes variables d'environnement.

- [Ce qu'il faut à Comégusto](#ce-quil-faut-à-comégusto)
- [Quel hébergeur choisir ?](#quel-hébergeur-choisir-)
- [Option A : un serveur (VPS) avec Docker et Caddy](#option-a--un-serveur-vps-avec-docker-et-caddy)
- [Option B : une plateforme PaaS](#option-b--une-plateforme-paas)
- [Médias sur un stockage compatible S3](#médias-sur-un-stockage-compatible-s3)
- [Tâches planifiées](#tâches-planifiées)
- [Sauvegardes, mises à jour et supervision](#sauvegardes-mises-à-jour-et-supervision)
- [Checklist de mise en production](#checklist-de-mise-en-production)

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

> Offres relevées en octobre 2026. Les conditions des offres gratuites changent souvent : vérifiez-les sur le site de l'hébergeur avant de vous engager.

### Gratuit

| Combinaison | Pour qui | Points d'attention |
| --- | --- | --- |
| **Oracle Cloud Always Free** (VM Arm) + [option A](#option-a--un-serveur-vps-avec-docker-et-caddy) | La solution gratuite la plus complète : tout tourne sur la VM, y compris PostgreSQL et le planificateur | Création de compte avec carte bancaire, capacité Arm parfois indisponible selon la région. L'allocation Always Free varie selon les sources (jusqu'à 4 cœurs et 24 Go, ou moins) : vérifiez la page officielle. |
| **Render** (web gratuit) + **Neon** (PostgreSQL gratuit) + **Cloudflare R2** (médias) + GitHub Actions (tâches) | Démonstration, petit trafic | L'instance gratuite Render se met en veille après 15 minutes sans visite (réveil d'environ une minute), 750 h par mois, ports SMTP bloqués. Le PostgreSQL gratuit de Render expire après 30 jours, d'où Neon (0,5 Go et 100 heures de calcul par mois sur l'offre gratuite). |
| **Google Cloud Run** + Neon + R2 + GitHub Actions | Démonstration avec un quota gratuit généreux | Compte de facturation Google obligatoire ; quota mensuel gratuit (180 000 vCPU-secondes, 2 millions de requêtes en facturation à la requête). |

À éviter : **PythonAnywhere gratuit**. L'accès internet sortant y est limité à une liste blanche, ce qui empêche d'interroger les services ouverts.

### Payant

| Hébergeur | Type | Prix indicatif | Pourquoi |
| --- | --- | --- | --- |
| **Hetzner Cloud**, **OVHcloud VPS**, **Scaleway Instances** | VPS + [option A](#option-a--un-serveur-vps-avec-docker-et-caddy) | Environ 4 à 10 € par mois | Meilleur rapport qualité-prix, contrôle total, hébergement en Europe. Hetzner a revu ses prix en 2026 et certaines gammes économiques ne sont plus toujours disponibles. |
| **Clever Cloud** | PaaS français | À l'usage, facturation à la seconde (calculateur sur le site) | Déploiement Docker, PostgreSQL managé avec sauvegardes quotidiennes, hébergement en France. |
| **Scalingo** | PaaS français | PostgreSQL Starter à partir de 7,20 € HT par mois, essai gratuit de 30 jours | Simple, hébergement en France, option SecNumCloud. |
| **Railway** | PaaS | Offre Hobby à 5 $ par mois, incluant 5 $ de consommation | Très simple, déjà utilisé par l'ancienne version du projet. |
| **Render** (instances payantes) | PaaS | À partir de quelques dollars par mois | Supprime la mise en veille et les limites de l'offre gratuite. |
| **Koyeb** | PaaS | Offre Pro à 29 $ par mois, incluant 10 $ de consommation | Racheté par Mistral AI en 2026, le service continue. |

**Notre recommandation** : un petit VPS européen avec l'option A (environ 5 € par mois, tout compris). Pour un projet de démonstration sans budget : Oracle Cloud Always Free avec la même option A, ou Render + Neon + R2.

## Option A : un serveur (VPS) avec Docker et Caddy

Tout tourne sur une seule machine : application, PostgreSQL, Redis, planificateur et [Caddy](https://caddyserver.com), qui obtient et renouvelle automatiquement le certificat HTTPS et sert les médias.

### 1. Préparer le serveur

- Une VM Ubuntu ou Debian récente, 1 Go de RAM minimum (2 Go confortables), architecture x86 ou Arm.
- Un nom de domaine dont l'enregistrement DNS `A` (et `AAAA` si IPv6) pointe vers l'IP du serveur.
- Les ports 80 et 443 ouverts (pare-feu du serveur et, chez Oracle ou Scaleway, groupe de sécurité).

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # puis se reconnecter
```

### 2. Récupérer le projet et le configurer

```bash
git clone https://github.com/Aziguy/reaco_updated.git comegusto && cd comegusto
cp .env.example .env
```

Dans `.env`, au minimum :

```ini
DEBUG=false
DOMAIN=comegusto.example.org
SECRET_KEY=une-longue-chaine-aleatoire
POSTGRES_PASSWORD=un-mot-de-passe-solide
EMAIL_URL=smtp+tls://utilisateur:motdepasse@smtp.example.org:587
DEFAULT_FROM_EMAIL=Comégusto <bonjour@example.org>
CONTACT_EMAIL=contact@example.org
ADMIN_URL=gestion-8f3k/
```

Pour générer une clé secrète : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`.

### 3. Lancer

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py sync_prices
```

Le site est disponible sur `https://DOMAIN` après quelques secondes (le temps d'obtenir le certificat). Les migrations sont appliquées automatiquement au démarrage, et le service `scheduler` lance la synchronisation des prix et les rappels une fois par jour.

### 4. Mettre à jour

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

## Option B : une plateforme PaaS

Le principe est le même sur Render, Railway, Clever Cloud, Scalingo, Koyeb ou Cloud Run : la plateforme construit l'image à partir du `Dockerfile` et l'exécute.

1. **Base de données** : créez un PostgreSQL (celui de la plateforme ou Neon) et récupérez son URL de connexion.
2. **Médias** : sur la plupart des PaaS, le disque est effacé à chaque déploiement. Configurez un [stockage S3](#médias-sur-un-stockage-compatible-s3).
3. **Service web** : créez un service à partir du dépôt GitHub, de type Docker, port `8000`, chemin de vérification de santé `/health/`.
4. **Variables d'environnement** :

   | Variable | Valeur |
   | --- | --- |
   | `SECRET_KEY` | chaîne aléatoire longue |
   | `ALLOWED_HOSTS` | `comegusto.onrender.com,comegusto.example.org` |
   | `CSRF_TRUSTED_ORIGINS` | `https://comegusto.example.org` |
   | `DATABASE_URL` | URL PostgreSQL (ajoutez `?sslmode=require` pour Neon) |
   | `AWS_*` | voir la section S3 |
   | `EMAIL_URL`, `DEFAULT_FROM_EMAIL`, `CONTACT_EMAIL` | votre SMTP |
   | `REDIS_URL` | facultatif |

5. **Premier lancement** : depuis le shell de la plateforme, exécutez `python manage.py createsuperuser`, `seed_demo` puis `sync_prices`. Sans shell disponible, lancez ces commandes depuis votre poste avec la même `DATABASE_URL`.
6. **Tâches quotidiennes** : utilisez les tâches cron de la plateforme si elles existent, sinon le [workflow GitHub fourni](#tâches-planifiées).

Particularités :

- **Render gratuit** : mise en veille après 15 minutes d'inactivité et SMTP bloqué. Pour les emails, passez à une instance payante.
- **Clever Cloud et Scalingo** : choisissez le déploiement Docker et ajoutez l'extension PostgreSQL ; l'URL de la base est fournie dans une variable que vous recopiez dans `DATABASE_URL`.
- **Cloud Run** : l'image se construit avec Cloud Build ou depuis GitHub. Définissez le port `8000` et une instance minimale à `0` pour rester dans le quota gratuit.

## Médias sur un stockage compatible S3

Les photos ajoutées depuis l'administration sont stockées dans `MEDIA_ROOT`. Sur un hébergeur sans disque persistant, activez un stockage objet en renseignant :

```ini
AWS_STORAGE_BUCKET_NAME=comegusto-media
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_ENDPOINT_URL=https://<compte>.r2.cloudflarestorage.com   # vide pour AWS S3
AWS_S3_REGION_NAME=auto                                         # selon le fournisseur
AWS_S3_CUSTOM_DOMAIN=media.example.org                          # facultatif, bucket public
```

- Sans domaine personnalisé, les images sont servies par des URL signées ; avec un domaine public, par des URL directes mises en cache.
- Le domaine des médias est ajouté automatiquement à la Content Security Policy.
- **Cloudflare R2** propose 10 Go gratuits et ne facture pas la bande passante sortante. Scaleway Object Storage et Backblaze B2 sont d'autres options européennes ou peu coûteuses.

## Tâches planifiées

| Hébergement | Solution |
| --- | --- |
| Option A (Docker Compose) | Le service `scheduler` s'en charge (intervalle réglable avec `SCHEDULER_INTERVAL`, en secondes). |
| PaaS avec cron | Planifiez `python manage.py sync_prices --pages 2` et `python manage.py send_expiry_reminders --base-url https://DOMAIN` chaque jour. |
| PaaS sans cron gratuit | Le workflow `.github/workflows/scheduled.yml` exécute ces commandes chaque nuit depuis GitHub Actions. Ajoutez dans les secrets du dépôt `DATABASE_URL` et `SECRET_KEY` (et `EMAIL_URL`, `SITE_URL` pour les rappels). Sans secret, le workflow ne fait rien. |

## Sauvegardes, mises à jour et supervision

- **Base de données (option A)** : une sauvegarde quotidienne par cron sur l'hôte, à copier hors du serveur :

  ```bash
  docker compose exec -T db pg_dump -U comegusto comegusto | gzip > backup-$(date +%F).sql.gz
  ```

  Restauration : `gunzip -c backup.sql.gz | docker compose exec -T db psql -U comegusto comegusto`.
- **Médias (option A)** : sauvegardez le volume Docker `media`.
- **PaaS** : activez les sauvegardes de la base proposées par la plateforme (souvent absentes des offres gratuites).
- **Supervision** : `/health/` renvoie `{"status": "ok"}` quand l'application et la base répondent. Branchez-y un service de surveillance (UptimeRobot, Better Stack, ou celui de la plateforme).
- **Journaux** : `docker compose logs -f web scheduler`.

## Checklist de mise en production

- [ ] `DEBUG=false` et `SECRET_KEY` unique, jamais commitée.
- [ ] `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` limités à vos domaines.
- [ ] HTTPS actif (Caddy ou plateforme), `SECURE_SSL_REDIRECT` et cookies sécurisés laissés à leur valeur par défaut.
- [ ] `ADMIN_URL` personnalisée et mot de passe administrateur robuste.
- [ ] SMTP configuré et `ACCOUNT_EMAIL_VERIFICATION=mandatory` si l'inscription est ouverte au public.
- [ ] Médias persistants (volume ou S3) et sauvegardes de la base.
- [ ] `python manage.py check --deploy` sans avertissement.
- [ ] Tâche quotidienne de synchronisation des prix en place.

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
