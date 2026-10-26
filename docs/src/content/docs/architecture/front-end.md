---
title: Front-end
description: Templates Django, HTMX, Tailwind CSS v4 et contraintes de la CSP.
sidebar:
  order: 5
---

Le front-end est rendu par Django. Pas de bundler JavaScript : htmx est vendorisé dans `static/vendor/htmx.min.js` et quelques comportements sont regroupés dans `static/js/app.js`.

## Templates

- `templates/base.html` : squelette commun. Il charge `js/theme.js` de façon synchrone (pour appliquer le thème sombre sans flash), puis htmx et `js/app.js` en `defer`. Le jeton CSRF est transmis à toutes les requêtes HTMX par `hx-headers` sur `<body>`.
- Un dossier par application (`templates/recipes/`, `templates/pantry/`...). Les fichiers préfixés par `_` sont des fragments renvoyés aux requêtes HTMX.
- `templates/partials/` : en-tête, pied de page, messages, carte de recette, champ de formulaire (`field.html`), lien de pagination, offres de prix, logo.
- `templates/allauth/layouts/base.html` : intègre les pages d'authentification d'allauth au gabarit du site.

### Balises `comegusto`

`{% load comegusto %}` donne accès à :

| Balise ou filtre | Rôle |
| --- | --- |
| `{% icon "nom" "classes" %}` | Icône SVG en ligne (jeu d'icônes défini dans `ICONS`) |
| `{{ valeur\|euro }}` | Montant au format français |
| `{{ valeur\|co2 }}` | Empreinte carbone lisible |
| `{{ minutes\|duration }}` | Durée en heures et minutes |
| `{% nav_current "/prefixe/" %}` | Marque le lien de navigation actif |

## HTMX

Les vues renvoient un fragment quand `request.htmx` est vrai (`django-htmx`). Motifs utilisés :

| Motif | Exemple |
| --- | --- |
| Formulaire de filtres qui remplace une zone de résultats | Liste des recettes : `hx-get` sur le formulaire, `hx-target="#results"`, déclenché au changement et à la saisie (délai de 400 ms) |
| URL partageable | La vue de liste renvoie `HX-Push-Url` avec les seuls paramètres utiles |
| Chargement différé | Panneau des prix d'une recette : `hx-trigger="load"` |
| Action sur une ligne | Garde-manger et courses : `hx-post` puis `hx-swap="outerHTML"` sur l'élément |

Les formulaires principaux (filtres, ajout au garde-manger, profil) gardent une `action` classique et fonctionnent aussi sans HTMX ; les actions sur une ligne (cocher, consommé, jeté) nécessitent JavaScript.

## Comportements JavaScript

`static/js/app.js` repose sur des attributs `data-*` et la délégation d'événements, jamais sur des gestionnaires en ligne :

| Attribut | Effet |
| --- | --- |
| `data-theme-toggle` | Bascule le thème sombre (mémorisé dans `localStorage`) |
| `data-menu-toggle` + `aria-controls` | Ouvre ou ferme un menu ou un panneau |
| `data-confirm` | Demande confirmation avant l'envoi d'un formulaire |
| `data-autosubmit` | Envoie le formulaire au changement de valeur |
| `data-print` | Lance l'impression |
| `data-geolocate` | Remplit latitude et longitude depuis la géolocalisation du navigateur |
| `data-scanner`, `data-scan` | Scan de code-barres avec l'API `BarcodeDetector` et la caméra |
| `img[data-logo]` | Remplace un logo d'enseigne introuvable par une icône |

## Tailwind CSS v4

- Source : `assets/app.css`, compilée vers `static/css/app.css` (`npm run build`, ou `npm run dev` en continu). Le fichier généré n'est pas versionné ; l'image Docker le compile dans une étape Node.
- Tailwind analyse `templates/`, `apps/` et `static/js/` (`@source`) : une classe construite dynamiquement en Python ou en JavaScript doit apparaître en entier dans le code.
- Couleurs de la marque dans `@theme` (`brand-50` à `brand-950`, `accent-400` à `accent-600`).
- Mode sombre par classe : `@custom-variant dark (&:where(.dark, .dark *))`, la classe `dark` étant posée sur `<html>` par `theme.js`.
- Composants réutilisables déclarés avec `@utility` (Tailwind v4 n'accepte pas `@apply` sur des classes personnalisées) : `container-page`, `card`, `btn`, `btn-primary`, `btn-secondary`, `btn-ghost`, `btn-danger`, `btn-sm`, `badge` et ses variantes, `nav-link`, `section-title`, `muted`, `stat`, `grade-a` à `grade-e`, `input`...

## Contraintes de la CSP

La Content Security Policy (`django-csp`) n'autorise que les ressources du site :

- **aucun script en ligne** : ni `<script>` dans un template, ni `onclick`, `onchange`... Ajoutez un comportement dans `static/js/app.js` avec un attribut `data-*` ;
- **aucun style en ligne** : ni `<style>`, ni attribut `style=`. Utilisez des classes Tailwind ; pour une barre de progression, l'élément `<progress>` ;
- **images** : le site, `data:`, les domaines Open Food Facts, `raw.githubusercontent.com` (logos d'enseignes) et le domaine du stockage S3 s'il est configuré.

Seule la documentation Swagger de l'API (`/api/docs/`) assouplit `style-src` pour ses propres styles. Voir [Sécurité](/reaco_updated/architecture/securite/).

## Accessibilité

Navigation au clavier avec contour de focus visible, `aria-expanded` et `aria-controls` sur les boutons qui ouvrent un panneau, `aria-pressed` sur les cases à cocher HTMX, `alt` sur toutes les images.
