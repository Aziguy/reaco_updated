"""Single source for the user guide: chapters, figures and their callouts.

Figures are captured by `manage.py capture_guide`, which reads the selectors below.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Callout:
    selector: str
    title: str
    text: str = ""


@dataclass(frozen=True)
class Figure:
    name: str
    path: str
    caption: str
    callouts: tuple[Callout, ...]
    auth: bool = True
    clip: str | None = None
    width: int = 1280
    height: int = 860
    mobile: bool = False
    actions: tuple[tuple[str, str], ...] = ()
    wait_for: str | None = None


@dataclass(frozen=True)
class Chapter:
    slug: str
    title: str
    summary: str
    icon: str
    figures: tuple[str, ...] = field(default=())

    @property
    def template(self) -> str:
        return f"guide/chapters/{self.slug}.html"


FIGURES = {
    figure.name: figure
    for figure in [
        Figure(
            name="home",
            path="/",
            auth=False,
            caption="La page d'accueil de Comégusto.",
            callouts=(
                Callout(
                    'nav[aria-label="Navigation principale"]',
                    "Menu principal",
                    "Recettes, anti-gaspi, garde-manger, courses et produits de saison.",
                ),
                Callout(
                    "[data-theme-toggle]",
                    "Thème clair ou sombre",
                    "Votre choix est mémorisé sur cet appareil.",
                ),
                Callout(
                    'header a[href="/compte/signup/"]',
                    "Créer un compte",
                    "Gratuit, il suffit d'une adresse email.",
                ),
                Callout(
                    "main section dl",
                    "Chiffres clés",
                    "Recettes chiffrées, prix réels et magasins couverts.",
                ),
            ),
        ),
        Figure(
            name="signup",
            path="/compte/signup/",
            auth=False,
            clip="main form",
            height=900,
            caption="Le formulaire d'inscription.",
            callouts=(
                Callout("#id_email", "Adresse email", "Elle sert d'identifiant de connexion."),
                Callout(
                    "#id_password1",
                    "Mot de passe",
                    "Au moins 8 caractères, à saisir deux fois.",
                ),
                Callout('main form button[type="submit"]', "Valider l'inscription"),
            ),
        ),
        Figure(
            name="dashboard",
            path="/tableau-de-bord/",
            caption="Le tableau de bord après connexion.",
            height=980,
            callouts=(
                Callout("main dl", "Indicateurs", "Stock, produits urgents et taux anti-gaspi."),
                Callout(
                    'main section:has(h2:text-is("À consommer vite"))',
                    "À consommer vite",
                    "Les produits dont la date approche.",
                ),
                Callout(
                    'main section:has(h2:text-is("Idées pour vider le frigo"))',
                    "Idées de recettes",
                    "Classées selon ce que vous avez déjà.",
                ),
                Callout(
                    'main section:has(h2:text-is("Listes de courses"))',
                    "Listes de courses",
                    "Vos listes actives, en un clic.",
                ),
            ),
        ),
        Figure(
            name="recipes-list",
            path="/recettes/",
            auth=False,
            caption="La liste des recettes et ses filtres.",
            callouts=(
                Callout(
                    ".field:has(#id_q)",
                    "Recherche",
                    "Par titre, ingrédient ou régime, sans accents.",
                ),
                Callout(
                    ".field:has(#id_sort)", "Tri", "Récentes, moins chères, rapides ou bas carbone."
                ),
                Callout("#more-filters", "Filtres", "Type de plat, régime, difficulté et durée."),
                Callout(
                    "#results article >> nth=0",
                    "Fiche recette",
                    "Coût par portion, durée, difficulté et empreinte carbone.",
                ),
            ),
        ),
        Figure(
            name="recipes-filters-mobile",
            path="/recettes/",
            auth=False,
            mobile=True,
            width=390,
            height=844,
            actions=(("click", '[aria-controls="more-filters"]'),),
            caption="Sur mobile, les filtres secondaires se déplient.",
            callouts=(
                Callout(
                    '[aria-controls="more-filters"]',
                    "Plus de filtres",
                    "Affiche le nombre de filtres actifs.",
                ),
                Callout("#more-filters", "Filtres dépliés"),
            ),
        ),
        Figure(
            name="recipe-detail",
            path="/recettes/ratatouille/",
            caption="L'en-tête d'une recette.",
            callouts=(
                Callout(
                    "main dl >> nth=0", "En bref", "Préparation, cuisson, difficulté, carbone."
                ),
                Callout(
                    "[hx-post*='favori']",
                    "Favori",
                    "Retrouvez la recette dans « Mes favoris ».",
                ),
                Callout('a[href="#courses"]', "Ajouter à mes courses"),
            ),
        ),
        Figure(
            name="recipe-ingredients",
            path="/recettes/ratatouille/",
            clip='section[aria-labelledby="ingredients-title"]',
            caption="Les ingrédients s'adaptent au nombre de portions.",
            callouts=(
                Callout(
                    '[role="group"][aria-label="Nombre de portions"]',
                    "Portions",
                    "Les quantités et le coût sont recalculés.",
                ),
                Callout(
                    '[title="Dans votre garde-manger"] >> nth=0',
                    "Déjà chez vous",
                    "L'ingrédient est dans votre garde-manger.",
                ),
                Callout(
                    "#ingredients .badge-brand >> nth=0",
                    "De saison",
                    "Produit de saison ce mois-ci selon l'ADEME.",
                ),
            ),
        ),
        Figure(
            name="recipe-steps",
            path="/recettes/ratatouille/",
            clip='section[aria-labelledby="steps-title"]',
            caption="Les étapes et les valeurs nutritionnelles.",
            callouts=(
                Callout('section[aria-labelledby="steps-title"] ol', "Étapes numérotées"),
                Callout(
                    'section[aria-labelledby="steps-title"] dl',
                    "Valeurs nutritionnelles",
                    "Par portion, calculées avec la table Ciqual de l'Anses.",
                ),
            ),
        ),
        Figure(
            name="recipe-prices",
            path="/recettes/ratatouille/",
            clip='section[aria-labelledby="prices-title"]',
            wait_for="#prices .card:not(.animate-pulse)",
            actions=(("click", "#prices summary"),),
            height=1400,
            caption="Le coût de la recette et la comparaison des enseignes.",
            callouts=(
                Callout(
                    "#prices .card > div.flex >> nth=0",
                    "Coût de la recette",
                    "Total, par portion et part des ingrédients chiffrés.",
                ),
                Callout(
                    "#prices table", "Détail par ingrédient", "Prix médian et nombre de relevés."
                ),
                Callout("#prices ol li >> nth=0", "Enseigne la moins chère"),
                Callout(
                    "#prices ol li >> nth=1",
                    "Autres enseignes",
                    "Prix relevés dans l'enseigne, complétés par une estimation.",
                ),
            ),
        ),
        Figure(
            name="recipe-add-to-list",
            path="/recettes/ratatouille/",
            clip="#courses",
            caption="Ajouter une recette à une liste de courses.",
            callouts=(
                Callout("#add-servings", "Portions"),
                Callout("#add-list", "Liste", "Une liste existante ou une nouvelle."),
                Callout(
                    'input[name="use_pantry"]',
                    "Déduire mon garde-manger",
                    "Les ingrédients déjà en stock ne sont pas ajoutés.",
                ),
                Callout('#courses button[type="submit"]', "Ajouter"),
            ),
        ),
        Figure(
            name="pantry-list",
            path="/garde-manger/",
            height=1000,
            caption="Le garde-manger, trié par urgence.",
            callouts=(
                Callout('header a[href="/garde-manger/ajouter/"]', "Ajouter un produit"),
                Callout(
                    "#pantry-stats",
                    "Indicateurs",
                    "Stock, urgences, taux anti-gaspi, valeur jetée.",
                ),
                Callout("main section h2 >> nth=0", "Groupes par urgence"),
                Callout(
                    "main section li .flex.flex-wrap.gap-1 >> nth=0",
                    "Consommé ou jeté",
                    "Sortez le produit du stock pour suivre votre gaspillage.",
                ),
            ),
        ),
        Figure(
            name="pantry-add",
            path="/garde-manger/ajouter/",
            height=1100,
            caption="Ajouter un produit, avec ou sans code-barres.",
            callouts=(
                Callout("#id_code", "Code-barres", "Saisissez les chiffres sous le code."),
                Callout("[data-scan]", "Scanner", "Utilise la caméra du téléphone."),
                Callout(
                    ".field:has(#id_ingredient)",
                    "Ingrédient",
                    "Le relie aux recettes et aux suggestions.",
                ),
                Callout(
                    ".field:has(#id_expires_on)",
                    "Date limite",
                    "Déclenche les alertes et les rappels.",
                ),
            ),
        ),
        Figure(
            name="anti-gaspi",
            path="/anti-gaspi/",
            height=1000,
            caption="Les idées de recettes anti-gaspi.",
            callouts=(
                Callout("main section.rounded-2xl", "À consommer en priorité"),
                Callout("main article >> nth=0", "Recette suggérée"),
                Callout(
                    "main article .badge-brand >> nth=0",
                    "Taux de correspondance",
                    "Part des ingrédients que vous avez déjà.",
                ),
            ),
        ),
        Figure(
            name="shopping-list",
            path="{shopping_list}",
            height=1000,
            caption="Une liste de courses classée par rayon.",
            callouts=(
                Callout('form[action*="articles"]', "Article libre", "Ajoutez ce que vous voulez."),
                Callout(
                    "main ul.card li button >> nth=0", "Cocher", "Au fur et à mesure des achats."
                ),
                Callout(
                    'form[action*="ranger"] button',
                    "Ranger les achats",
                    "Les articles cochés vont au garde-manger.",
                ),
                Callout(
                    "aside > div", "Où faire ses courses ?", "Le panier comparé entre enseignes."
                ),
            ),
        ),
        Figure(
            name="season",
            path="/saison/",
            auth=False,
            caption="Le calendrier des fruits et légumes de saison.",
            callouts=(
                Callout("#mois", "Mois", "Choisissez un autre mois."),
                Callout(
                    "main .grid section >> nth=0",
                    "Produits de saison",
                    "Avec leur empreinte carbone au kilo.",
                ),
            ),
        ),
        Figure(
            name="profile",
            path="/compte/profil/",
            height=1150,
            caption="Votre profil.",
            callouts=(
                Callout(
                    ".field:has(#id_postal_code)",
                    "Code postal",
                    "Pour comparer les magasins proches.",
                ),
                Callout(".field:has(#id_search_radius_km)", "Rayon de recherche"),
                Callout(
                    "[data-geolocate]", "Ma position", "Remplit la localisation automatiquement."
                ),
                Callout("#id_expiry_reminders", "Rappels par email"),
                Callout('main section:has(h2:text-is("Sécurité"))', "Sécurité"),
            ),
        ),
    ]
}

CHAPTERS = [
    Chapter(
        "premiers-pas",
        "Premiers pas",
        "Découvrir Comégusto, créer un compte et lire le tableau de bord.",
        "home",
        ("home", "signup", "dashboard"),
    ),
    Chapter(
        "recettes",
        "Trouver une recette",
        "Rechercher, filtrer, adapter les portions et lire une fiche.",
        "chef",
        (
            "recipes-list",
            "recipes-filters-mobile",
            "recipe-detail",
            "recipe-ingredients",
            "recipe-steps",
        ),
    ),
    Chapter(
        "prix",
        "Comprendre les prix",
        "D'où viennent les prix et comment comparer les enseignes.",
        "euro",
        ("recipe-prices",),
    ),
    Chapter(
        "garde-manger",
        "Garde-manger",
        "Ajouter vos produits, scanner un code-barres et suivre les dates.",
        "fridge",
        ("pantry-list", "pantry-add"),
    ),
    Chapter(
        "anti-gaspi",
        "Cuisiner anti-gaspi",
        "Trouver quoi cuisiner avec ce que vous avez déjà.",
        "leaf",
        ("anti-gaspi",),
    ),
    Chapter(
        "courses",
        "Listes de courses",
        "Préparer, compléter et ranger vos courses.",
        "cart",
        ("recipe-add-to-list", "shopping-list"),
    ),
    Chapter(
        "saison",
        "Produits de saison",
        "Choisir des fruits et légumes moins chers et moins émetteurs.",
        "sprout",
        ("season",),
    ),
    Chapter(
        "compte",
        "Mon compte",
        "Profil, localisation, rappels, sécurité et suppression.",
        "user",
        ("profile",),
    ),
    Chapter(
        "faq",
        "Questions fréquentes",
        "Données, confidentialité et réponses aux questions courantes.",
        "help",
    ),
]

CHAPTERS_BY_SLUG = {chapter.slug: chapter for chapter in CHAPTERS}
