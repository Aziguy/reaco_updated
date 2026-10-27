---
title: Guide utilisateur intégré
description: Fonctionnement et mise à jour du guide utilisateur intégré à l'application.
sidebar:
  order: 4
---

L'application contient un guide utilisateur complet, accessible sur `/guide/` depuis l'icône d'aide de l'en-tête, le pied de page et les liens « Aide » des pages principales. Chaque chapitre est illustré de captures annotées : des repères numérotés sur l'image renvoient à une légende.

## Organisation

| Élément | Rôle |
| --- | --- |
| `apps/guide/content.py` | Source unique : chapitres (`CHAPTERS`) et figures (`FIGURES`) avec leurs repères |
| `templates/guide/chapters/<slug>.html` | Texte de chaque chapitre |
| `templates/guide/_figure.html` | Rendu d'une figure : image claire et sombre, légende numérotée |
| `{% guide_figure "nom" %}` | Balise qui insère une figure dans un chapitre (`apps/guide/templatetags/guide.py`) |
| `static/img/guide/` | Captures `<nom>-light.webp` et `<nom>-dark.webp`, et `manifest.json` (dimensions) |
| `capture_guide` | Commande qui produit les captures à partir de `FIGURES` |

Une figure est décrite une seule fois :

```python
Figure(
    name="pantry-add",
    path="/garde-manger/ajouter/",      # page à capturer
    caption="Ajouter un produit, avec ou sans code-barres.",
    height=1100,                         # hauteur de la fenêtre
    clip=None,                           # sélecteur pour recadrer sur une zone
    actions=(),                          # par exemple (("click", "#bouton"),)
                                         # ou (("set_input_files", "input[type=file]", "{receipt}"),)
    callouts=(
        Callout("#id_code", "Code-barres", "Saisissez les chiffres sous le code."),
        Callout("[data-scan]", "Scanner", "Utilise la caméra du téléphone."),
    ),
)
```

Les sélecteurs suivent la syntaxe Playwright : CSS, `:has()`, `:text-is()` et `>> nth=0` pour cibler le premier élément.

## Régénérer les captures

À faire après toute modification visible de l'interface (gabarit, styles, libellés) :

```bash
uv sync                                    # installe Playwright (groupe dev)
uv run playwright install chromium         # une seule fois
npm run build                              # styles à jour
DEBUG=true uv run python manage.py runserver
# dans un second terminal, sur la même base :
DEBUG=true uv run python manage.py capture_guide            # toutes les figures
DEBUG=true uv run python manage.py capture_guide pantry-add # une seule
```

La commande :

1. vérifie que le serveur répond sur `/health/` ;
2. prépare un compte de démonstration `guide@comegusto.local` (mot de passe aléatoire), avec un garde-manger, des favoris et une liste de courses réalistes, dates calculées à partir du jour ;
3. pour les figures de l'assistant, compose un menu, crée une recette « vider le frigo » et génère un ticket de caisse d'exemple, avec de vraies réponses de l'assistant (quelques centimes) ;
4. ouvre chaque page dans Chromium, en thème clair puis sombre (en mobile pour les figures `mobile=True`) ;
5. entoure chaque repère et ajoute son numéro, puis enregistre la capture en WebP et ses dimensions dans `manifest.json`.

Un sélecteur introuvable arrête la commande avec le nom de la figure : corrigez `content.py` ou le gabarit. Vérifiez ensuite le rendu sur `/guide/`, puis committez les images avec la modification de l'interface.

:::note
Les captures dépendent des données de la base (recettes, prix synchronisés) et du mois en cours (produits de saison). Utilisez une base chargée avec `seed_demo` et `sync_prices` pour un rendu représentatif.
:::

:::caution[Figures de l'assistant]
Elles exigent un fournisseur configuré (`ANTHROPIC_API_KEY` dans `.env`, puis `setup_assistant`). Sans assistant, la commande s'arrête sur ces figures : capturez les autres en les nommant.
:::

## Ajouter une figure ou un chapitre

1. Déclarez la figure dans `FIGURES` et ajoutez son nom au tuple `figures` du chapitre.
2. Insérez `{% guide_figure "nom" %}` dans le gabarit du chapitre, à l'endroit voulu.
3. Lancez `capture_guide nom`.
4. Pour un nouveau chapitre, ajoutez un `Chapter` dans `CHAPTERS` (ordre d'affichage) et créez `templates/guide/chapters/<slug>.html`.

Les tests (`apps/guide/tests/`) vérifient que chaque chapitre s'affiche, que chaque figure appartient à un chapitre, que ses images existent dans les deux thèmes et que les légendes sont rendues.

## Rédaction

- Phrases courtes, à l'impératif pour les actions (« Cliquez sur **Ajouter** »).
- Libellés de l'interface en gras, exactement comme à l'écran.
- Un encadré `guide-note` pour une précision, `guide-warning` pour une mise en garde.
- Pas de script ni de style en ligne : la CSP les bloque, comme partout ailleurs.
