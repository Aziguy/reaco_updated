---
title: Décisions d'architecture
description: Choix structurants du projet, leur contexte et leurs conséquences.
sidebar:
  order: 3
---

Chaque décision suit le même format : contexte, décision, conséquences. Pour en ajouter une, numérotez-la à la suite et liez l'issue correspondante.

## 1. Django et HTMX plutôt qu'une application monopage

- **Contexte** : refonte d'un ancien projet Django ; équipe réduite ; besoin d'un site rapide, accessible et facile à maintenir.
- **Décision** : Django 5.2 LTS rendu côté serveur, interactions partielles avec HTMX, aucun framework JavaScript.
- **Conséquences** : une seule base de code et un seul langage métier, pas de build JavaScript, bon référencement. Les interactions très riches (édition hors ligne, glisser-déposer) seraient plus coûteuses à construire.

## 2. Données ouvertes plutôt qu'API commerciales

- **Contexte** : l'application doit rester gratuite à héberger et indépendante d'un fournisseur.
- **Décision** : Open Prices, Open Food Facts, ADEME Impact CO2, Anses Ciqual et IGN.
- **Conséquences** : couverture des prix inégale selon les produits et les régions. L'estimateur affiche donc la part de prix réellement relevés et revient à une estimation nationale quand les données locales manquent.

## 3. Médiane des relevés et préférence pour le vrac

- **Contexte** : les catégories Open Food Facts larges mélangent produits bruts et transformés ; les prix extrêmes faussent une moyenne.
- **Décision** : prix de référence = médiane hors promotions ; prix en vrac préférés dès 5 relevés ; une enseigne n'est comparée que si 40 % des ingrédients y ont un vrai relevé.
- **Conséquences** : estimations robustes aux valeurs aberrantes, au prix d'un réglage manuel des catégories d'ingrédients.

## 4. Métriques précalculées

- **Contexte** : coût, CO2 et nutrition servent au tri et aux filtres de la liste des recettes.
- **Décision** : valeurs stockées sur `Recipe`, recalculées après chaque synchronisation, chaque `seed_demo` et chaque enregistrement dans l'administration.
- **Conséquences** : listes rapides et triables en SQL ; les valeurs peuvent avoir jusqu'à un jour de retard sur les derniers prix.

## 5. Client HTTP commun tolérant aux pannes

- **Contexte** : les services ouverts sont gratuits et parfois lents ou indisponibles.
- **Décision** : `JsonClient` unique avec délai maximal, nouvelles tentatives, cache des réponses et cache des pannes de 5 minutes.
- **Conséquences** : aucune page ne reste bloquée par un service tiers ; chaque appelant doit prévoir un état dégradé.

## 6. Recherche par index normalisé

- **Contexte** : recherche insensible aux accents, identique sur SQLite (développement, tests) et PostgreSQL (production).
- **Décision** : champ `search_text` en minuscules sans accents, mis à jour par `save()` et des signaux, recherche mot par mot avec `contains`.
- **Conséquences** : portable et suffisant pour quelques milliers de recettes ; au-delà, passer à la recherche plein texte PostgreSQL.

## 7. CSP stricte

- **Contexte** : réduire la surface d'attaque XSS d'une application avec comptes et données personnelles.
- **Décision** : aucun script ni style en ligne, ressources limitées au site et à quelques domaines d'images.
- **Conséquences** : comportements JavaScript centralisés dans `static/js/app.js` via des attributs `data-*` ; certaines bibliothèques tierces sont inutilisables sans adaptation.

## 8. uv pour Python, Tailwind CSS v4 pour les styles

- **Contexte** : installation reproductible et rapide ; styles cohérents sans framework CSS lourd.
- **Décision** : uv (`pyproject.toml` et `uv.lock`), Tailwind CSS v4 compilé par sa CLI, composants en `@utility`.
- **Conséquences** : Node.js n'est nécessaire que pour compiler les styles (étape dédiée du `Dockerfile`).

## 9. Docker générique et Caddy

- **Contexte** : déploiement possible aussi bien sur un VPS que sur un PaaS.
- **Décision** : une image unique, Docker Compose pour le développement et la production, Caddy pour HTTPS et les médias, S3 facultatif.
- **Conséquences** : pas de dépendance à un hébergeur ; les tâches planifiées passent par un service `scheduler`, un cron de plateforme ou GitHub Actions.

## 10. Documentation avec Astro Starlight

- **Contexte** : documentation développeur publiée sur GitHub Pages, en français, avec recherche et diagrammes. Material for MkDocs n'est plus maintenu au-delà de novembre 2026.
- **Décision** : Astro Starlight dans `docs/`, diagrammes Mermaid, publication par GitHub Actions.
- **Conséquences** : la documentation vit dans le dépôt et suit les pull requests ; Node.js est nécessaire pour la construire.
