---
title: Serveur VPS
description: Déployer Comégusto sur un serveur avec Docker Compose et Caddy.
sidebar:
  order: 2
---

Tout tourne sur une seule machine : application, PostgreSQL, Redis, planificateur et [Caddy](https://caddyserver.com), qui obtient et renouvelle automatiquement le certificat HTTPS et sert les médias.

## 1. Préparer le serveur

- Une VM Ubuntu ou Debian récente, 1 Go de RAM minimum (2 Go confortables), architecture x86 ou Arm.
- Un nom de domaine dont l'enregistrement DNS `A` (et `AAAA` si IPv6) pointe vers l'IP du serveur.
- Les ports 80 et 443 ouverts (pare-feu du serveur et, chez Oracle ou Scaleway, groupe de sécurité).

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER   # puis se reconnecter
```

## 2. Récupérer le projet et le configurer

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

Pour générer une clé secrète : `python3 -c "import secrets; print(secrets.token_urlsafe(50))"`. Pour choisir un fournisseur d'emails et écrire `EMAIL_URL`, voir [Configurer les emails](/reaco_updated/deploiement/configuration/#emails).

`docker-compose.prod.yml` dérive de `DOMAIN` les variables `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` et `SITE_URL`, force HTTPS et les cookies sécurisés, et confie les médias à Caddy (`SERVE_MEDIA=false`).

## 3. Lancer

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py seed_demo
docker compose exec web python manage.py sync_prices
```

Le site est disponible sur `https://DOMAIN` après quelques secondes (le temps d'obtenir le certificat). Les migrations sont appliquées automatiquement au démarrage, et le service `scheduler` lance la synchronisation des prix et les rappels une fois par jour.

## 4. Mettre à jour

```bash
git pull
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Avant une mise à jour importante, faites une [sauvegarde de la base](/reaco_updated/deploiement/mise-en-production/#sauvegardes).
