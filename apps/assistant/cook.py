"""What to cook with what one has: the dish, what is missing and where to buy it for less."""

import re
from dataclasses import dataclass, field
from decimal import Decimal

from apps.core.text import normalize
from apps.integrations.geocoding import geocode_city
from apps.integrations.http import ServiceError
from apps.pantry.models import PantryItem
from apps.pricing.estimator import BasketEstimate, Line, estimate, estimate_near
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient

from .search import ingredient_index, resolve

DEFAULT_RADIUS_KM = 10
MAX_HAVE = 30
SUGGESTIONS = 6
SEPARATORS = re.compile(r"\s*(?:,|;|\n|\bet\b|\+)\s*")
ARTICLES = re.compile(r"^(?:(?:de|des|du|la|le|les|un|une)\s+|[dl][^\w\s])+", re.I)
SERVINGS = re.compile(r"\s*\bpour\s+(\d{1,2})(?:\s*(?:personnes?|pers\.?|convives?))?\b", re.I)
STOP_WORDS = {"avec", "aux", "des", "les", "pour", "une", "facon", "maison", "plat", "recette"}


@dataclass
class Place:
    label: str
    near: tuple[float, float, int]


def split_names(text: str) -> list[str]:
    """ "des pommes, du riz et de l'ail" gives ["pommes", "riz", "ail"]."""
    names = (ARTICLES.sub("", part.strip()) for part in SEPARATORS.split(text or ""))
    return [name for name in names if len(name) > 1][:MAX_HAVE]


def parse_have(text: str) -> tuple[list[Ingredient], list[str]]:
    slugs, unknown = resolve(split_names(text), ingredient_index())
    found = Ingredient.objects.in_bulk(slugs, field_name="slug")
    return [found[slug] for slug in slugs if slug in found], unknown


def pantry_ingredients(user) -> list[Ingredient]:
    if not user or not user.is_authenticated:
        return []
    ids = (
        PantryItem.objects.filter(user=user, ingredient__isnull=False)
        .in_stock()
        .values_list("ingredient_id", flat=True)
    )
    return list(Ingredient.objects.filter(pk__in=set(ids)))


def split_dish(text: str) -> tuple[str, int | None]:
    """ "riz sauce tomate pour 2 personnes" gives ("riz sauce tomate", 2)."""
    match = SERVINGS.search(text or "")
    servings = int(match.group(1)) if match and 0 < int(match.group(1)) <= 12 else None
    dish = SERVINGS.sub(" ", text or "") if match else text or ""
    return " ".join(dish.split()).strip(" ,.;:!?"), servings


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", normalize(text))
    return {re.sub(r"(s|x)$", "", w) for w in words if len(w) > 2 and w not in STOP_WORDS}


def find_dish(dish: str, user) -> tuple[Recipe | None, list[Recipe]]:
    """A recipe whose title holds every word of the dish, and close recipes otherwise."""
    tokens = _tokens(dish)
    if not tokens:
        return None, []
    recipes = Recipe.objects.visible_to(user) if user else Recipe.objects.published()
    scored = []
    for recipe in recipes.only("pk", "title", "search_text", "is_published", "created_at"):
        title = _tokens(recipe.title)
        if tokens <= title:
            return Recipe.objects.with_relations().get(pk=recipe.pk), []
        hits = len(tokens & _tokens(recipe.search_text))
        if hits and hits * 2 >= len(tokens):
            scored.append((hits, len(tokens & title), recipe.is_published, recipe.pk))
    scored.sort(reverse=True)
    close = Recipe.objects.published().filter(pk__in=[row[3] for row in scored[:4]])
    return None, sorted(close, key=lambda r: [row[3] for row in scored].index(r.pk))


def locate(user, postal_code: str = "") -> Place | None:
    if postal_code:
        try:
            place = geocode_city(postal_code)
        except ServiceError:
            place = None
        if place:
            return Place(place.label, (place.latitude, place.longitude, DEFAULT_RADIUS_KM))
    if user and user.is_authenticated and user.has_location:
        label = " ".join(filter(None, [user.postal_code, user.city])) or "votre adresse"
        return Place(label, user.location)
    return None


@dataclass
class Need:
    item: RecipeIngredient
    quantity: str
    cost: Decimal | None = None


@dataclass
class CookPlan:
    recipe: Recipe
    servings: int
    have: list[Need] = field(default_factory=list)
    missing: list[Need] = field(default_factory=list)
    staples: list[Need] = field(default_factory=list)
    basket: BasketEstimate | None = None
    local: bool = False
    saving: Decimal = Decimal(0)

    @property
    def missing_total(self) -> Decimal | None:
        if not self.basket or not self.basket.total:
            return None
        return self.basket.cheapest.total if self.basket.cheapest else self.basket.total

    @property
    def best(self):
        return self.basket.cheapest if self.basket else None

    @property
    def needed(self) -> int:
        return len(self.have) + len(self.missing)

    @property
    def coverage(self) -> int:
        return round(100 * len(self.have) / self.needed) if self.needed else 0

    @property
    def have_ids(self) -> list[int]:
        return [need.item.ingredient_id for need in self.have]


def plan_for(recipe: Recipe, servings: int, have_ids: set[int], place: Place | None) -> CookPlan:
    """Split the recipe into what one has and what to buy, then price only what is missing."""
    factor = Decimal(servings) / recipe.servings
    plan = CookPlan(recipe=recipe, servings=servings)
    missing_lines = []
    for item in recipe.items.all():
        need = Need(item, item.display_quantity(factor))
        if item.ingredient.is_staple and item.ingredient_id not in have_ids:
            plan.staples.append(need)
        elif item.ingredient_id in have_ids:
            plan.have.append(need)
        else:
            plan.missing.append(need)
            missing_lines.append(Line(item.ingredient, item.scaled(factor), item.unit))
    if missing_lines:
        plan.basket, plan.local = estimate_near(missing_lines, place.near if place else None)
        costs = {line.ingredient.pk: line.cost for line in plan.basket.lines}
        for need in plan.missing:
            need.cost = costs.get(need.item.ingredient_id)
    if plan.have:
        lines = [Line(n.item.ingredient, n.item.scaled(factor), n.item.unit) for n in plan.have]
        plan.saving = estimate(lines).total
    return plan


def suggest(have_ids: set[int], user, servings: int, place: Place | None) -> list[CookPlan]:
    """Recipes needing the fewest purchases, then the cheapest missing basket."""
    if not have_ids:
        return []
    recipes = Recipe.objects.visible_to(user) if user else Recipe.objects.published()
    candidates = []
    for recipe in recipes.filter(items__ingredient_id__in=have_ids).distinct().with_relations():
        needed = [item for item in recipe.items.all() if not item.ingredient.is_staple]
        if not needed:
            continue
        matched = sum(item.ingredient_id in have_ids for item in needed)
        candidates.append((len(needed) - matched, -matched, recipe.pk, recipe))
    candidates.sort(key=lambda row: row[:3])
    plans = [plan_for(row[3], servings, have_ids, place) for row in candidates[:SUGGESTIONS]]
    plans.sort(key=lambda p: (len(p.missing), p.missing_total or Decimal(0)))
    return plans
