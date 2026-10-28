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
    actions: tuple[tuple[str, ...], ...] = ()
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


SEARCH_EXAMPLE = (
    "/assistant/recherche/?demande=Un+d%C3%AEner+v%C3%A9g%C3%A9tarien+pour+4+"
    "%C3%A0+moins+de+10+%E2%82%AC"
)

COOK_DISH = "/assistant/cuisiner/?envie=riz+jollof&j=riz%2C+oignon%2C+ail&personnes=2"
COOK_HAVE = "/assistant/cuisiner/?j=pommes%2C+riz%2C+ail%2C+oeufs&personnes=2"

FIGURES = {
    figure.name: figure
    for figure in [
        Figure(
            name="cook-dish",
            path=COOK_DISH,
            caption="Un plat, ce que vous avez déjà, ce qui manque et où l'acheter.",
            height=1500,
            callouts=(
                Callout("#cook-form #id_envie", "Votre envie", "Facultative, avec « pour 2 »."),
                Callout(
                    "#cook-have",
                    "Ce que vous avez",
                    "Tapez, photographiez ou comptez le garde-manger.",
                ),
                Callout('section[aria-labelledby="cook-missing"]', "À acheter"),
                Callout(
                    'aside[aria-label="Où acheter"] > div >> nth=0',
                    "Le moins cher",
                    "L'enseigne la moins chère près de chez vous, pour ce qui manque.",
                ),
                Callout(
                    'aside[aria-label="Où acheter"] form button',
                    "Liste de courses",
                    "Seuls les ingrédients manquants y sont ajoutés.",
                ),
            ),
        ),
        Figure(
            name="cook-suggestions",
            path=COOK_HAVE,
            caption="Les recettes qui demandent le moins d'achats.",
            height=2200,
            callouts=(
                Callout("#cook-results article >> nth=0", "Moins d'achats en tête"),
                Callout(
                    "#cook-results article >> nth=0 >> .border-t",
                    "Prix des manquants",
                    "Dans l'enseigne la moins chère.",
                ),
                Callout(
                    "#cook-results article.ai-surface",
                    "Recette sur mesure",
                    "L'assistant invente un plat avec vos ingrédients.",
                ),
            ),
        ),
        Figure(
            name="pricing",
            path="/abonnement/",
            auth=False,
            caption="Les formules Gratuit, Plus et Famille.",
            height=1300,
            callouts=(
                Callout("main fieldset.segmented", "Mensuel ou annuel"),
                Callout("main article >> nth=1", "Formule", "Prix et avantages."),
                Callout(
                    "main article >> nth=1 >> dl",
                    "Assistant IA par jour",
                    "Le nombre d'utilisations incluses.",
                ),
            ),
        ),
        Figure(
            name="billing-account",
            path="/abonnement/mon-abonnement/",
            caption="Votre formule et l'assistant IA du jour.",
            height=760,
            callouts=(
                Callout('section[aria-labelledby="plan-title"] .ai-surface', "Formule actuelle"),
                Callout(
                    'section[aria-labelledby="plan-title"] ul',
                    "Utilisations du jour",
                    "Remises à zéro chaque nuit.",
                ),
            ),
        ),
        Figure(
            name="home",
            path="/",
            auth=False,
            caption="La page d'accueil de Comégusto.",
            callouts=(
                Callout(
                    'nav[aria-label="Navigation principale"]',
                    "Menu principal",
                    "Recettes, assistant, anti-gaspi, garde-manger, courses et saison.",
                ),
                Callout(
                    "main form[role=search]",
                    "Recherche en une phrase",
                    "Décrivez votre envie, l'assistant trouve les recettes.",
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
            height=1180,
            callouts=(
                Callout(
                    "main form[role=search]",
                    "Recherche en une phrase",
                    "Confiée à l'assistant, voir le chapitre Assistant IA.",
                ),
                Callout(
                    ".field:has(#id_q)",
                    "Recherche",
                    "Par titre, ingrédient ou régime, sans accents.",
                ),
                Callout(
                    ".field:has(#id_sort)", "Tri", "Récentes, moins chères, rapides ou bas carbone."
                ),
                Callout(
                    "#more-filters",
                    "Filtres",
                    "Type de plat, cuisine, régime, difficulté et durée.",
                ),
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
                Callout('main a[href="/compte/2fa/"] >> nth=0', "Sécurité du compte"),
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
            ),
        ),
        Figure(
            name="security",
            path="/compte/2fa/",
            height=820,
            caption="La double authentification, depuis Sécurité du compte.",
            callouts=(
                Callout(
                    'main li:has(h2:text-is("Application d\'authentification"))',
                    "Application",
                    "Un code à 6 chiffres à chaque connexion.",
                ),
                Callout(
                    'main li:has(h2:text-is("Clés d\'accès"))',
                    "Clé d'accès",
                    "Empreinte, visage ou code de l'appareil.",
                ),
                Callout(
                    'main li:has(h2:text-is("Codes de secours"))',
                    "Codes de secours",
                    "Si vous perdez votre téléphone.",
                ),
            ),
        ),
        Figure(
            name="assistant-hub",
            path="/assistant/",
            caption="La page Assistant et ses outils.",
            height=1000,
            callouts=(
                Callout("main form[role=search]", "Recherche en une phrase"),
                Callout(
                    "main form[role=search] .segmented",
                    "Rapide ou Approfondi",
                    "Approfondi prend quelques secondes de plus pour les demandes complexes.",
                ),
                Callout(
                    'ul[aria-label="Exemples de demandes"]',
                    "Exemples",
                    "Un clic pour lancer une demande type.",
                ),
                Callout(
                    'section[aria-labelledby="tools-title"] .grid',
                    "Outils",
                    "Cuisiner, menu de la semaine, vider le frigo, ticket de caisse.",
                ),
            ),
        ),
        Figure(
            name="assistant-search",
            path=SEARCH_EXAMPLE,
            caption="Une recherche en langage naturel et les critères compris.",
            height=1200,
            wait_for="#ai-results .ai-chip",
            callouts=(
                Callout("main form[role=search] input[name=demande]", "Votre demande"),
                Callout(
                    "#ai-results section[aria-label]",
                    "Ce que l'assistant a compris",
                ),
                Callout(
                    "#ai-results .ai-chip-remove >> nth=1",
                    "Critères",
                    "La croix retire un critère, sans nouvel appel à l'assistant.",
                ),
                Callout(
                    "#ai-results article >> nth=0",
                    "Recettes",
                    "Prix et CO2 calculés par Comégusto.",
                ),
            ),
        ),
        Figure(
            name="assistant-plan-form",
            path="/assistant/menu/",
            caption="Les réglages du menu de la semaine.",
            clip="main form[data-ai-form]",
            height=1100,
            callouts=(
                Callout('fieldset:has(input[name="meals_per_day"])', "Repas"),
                Callout(".field:has(#id_budget)", "Budget total", "Facultatif, pour tout le menu."),
                Callout(
                    "label:has(#id_use_pantry)",
                    "Garde-manger",
                    "Les produits qui périment bientôt passent en premier.",
                ),
                Callout("main form[data-ai-form] .segmented", "Mode"),
                Callout('main form[data-ai-form] button[type="submit"]', "Composer mon menu"),
            ),
        ),
        Figure(
            name="assistant-plan",
            path="{plan}",
            caption="Un menu composé par l'assistant.",
            height=1500,
            wait_for="#plan",
            callouts=(
                Callout(
                    "#plan > section dl", "Bilan", "Coût, prix par portion, CO2 et produits sauvés."
                ),
                Callout(
                    "#plan ol > li >> nth=0",
                    "Repas du jour",
                    "Chaque choix est expliqué en une phrase.",
                ),
                Callout(
                    "#plan button[hx-post] >> nth=0",
                    "Changer",
                    "Propose un autre repas, sans nouvel appel à l'assistant.",
                ),
                Callout(
                    "#plan aside .card >> nth=0",
                    "Liste de courses",
                    "Tout le menu, moins ce que vous avez déjà.",
                ),
            ),
        ),
        Figure(
            name="assistant-fridge",
            path="/assistant/frigo/",
            caption="Choisir les produits à sauver.",
            clip="main form[data-ai-form]",
            height=1200,
            callouts=(
                Callout(
                    "main form[data-ai-form] fieldset .grid",
                    "Produits",
                    "Ceux qui périment bientôt sont déjà cochés.",
                ),
                Callout(".field:has(#id_wishes)", "Vos envies", "Par exemple « sans four »."),
                Callout('main form[data-ai-form] button[type="submit"]', "Créer ma recette"),
            ),
        ),
        Figure(
            name="assistant-recipe",
            path="{ai_recipe}",
            caption="Une recette créée par l'assistant, chiffrée par Comégusto.",
            height=1000,
            callouts=(
                Callout("section[data-ai-banner]", "Recette privée", "Visible par vous seul."),
                Callout(
                    'form[action$="/proposer/"] button',
                    "Proposer à la communauté",
                    "L'équipe la relit avant de la publier.",
                ),
                Callout("main dl >> nth=0", "Repères", "Temps, difficulté et empreinte carbone."),
            ),
        ),
        Figure(
            name="assistant-receipt",
            path="/assistant/ticket/",
            caption="Les achats lus sur un ticket, à vérifier avant l'ajout.",
            height=1100,
            actions=(
                ("set_input_files", "input[name=photo]", "{receipt}"),
                ("click", 'main form[data-ai-form] button[type="submit"]'),
            ),
            wait_for='form[action$="/ticket/ajouter/"]',
            callouts=(
                Callout(
                    'form[action$="/ticket/ajouter/"] li input[type=checkbox] >> nth=0',
                    "Garder",
                    "Décochez ce que vous ne voulez pas ajouter.",
                ),
                Callout(
                    'form[action$="/ticket/ajouter/"] li input[type=text] >> nth=0',
                    "Produit reconnu",
                    "Nom, quantité, unité et prix payé, modifiables.",
                ),
                Callout(
                    'form[action$="/ticket/ajouter/"] li input[type=date] >> nth=0',
                    "Date de péremption",
                ),
                Callout(
                    'form[action$="/ticket/ajouter/"] button[type="submit"]',
                    "Ajouter au garde-manger",
                ),
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
        "cuisiner",
        "Cuisiner avec ce que j'ai",
        "Votre envie, ce qui manque et le magasin le moins cher près de chez vous.",
        "cart",
        ("cook-dish", "cook-suggestions"),
    ),
    Chapter(
        "assistant",
        "Assistant IA",
        "Chercher en une phrase, composer un menu, vider le frigo, lire un ticket.",
        "sparkles",
        (
            "assistant-hub",
            "assistant-search",
            "assistant-plan-form",
            "assistant-plan",
            "assistant-fridge",
            "assistant-recipe",
            "assistant-receipt",
        ),
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
        "Profil, localisation, double authentification et suppression.",
        "user",
        ("profile", "security"),
    ),
    Chapter(
        "abonnement",
        "Formules et abonnement",
        "Gratuit, Plus ou Famille, paiement par virement ou Wero.",
        "heart",
        ("pricing", "billing-account"),
    ),
    Chapter(
        "faq",
        "Questions fréquentes",
        "Données, confidentialité et réponses aux questions courantes.",
        "help",
    ),
]

CHAPTERS_BY_SLUG = {chapter.slug: chapter for chapter in CHAPTERS}
