from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from statistics import median

from django.db.models import Count, Q, Sum
from django.utils import timezone

from apps.integrations import openfoodfacts, openprices
from apps.integrations.http import ServiceError
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.recipes.units import Unit

from .models import PantryItem

EXPIRING_WEIGHT = 3


def match_ingredient(product: openfoodfacts.Product) -> Ingredient | None:
    """Most specific ingredient matching the product categories (OFF lists them generic first)."""
    if not product.categories:
        return None
    candidates = Ingredient.objects.filter(off_category__in=product.categories)
    return max(candidates, key=lambda i: product.categories.index(i.off_category), default=None)


def product_price(code: str) -> Decimal | None:
    since = timezone.localdate() - timedelta(days=365)
    try:
        records = openprices.fetch_prices(product_code=code, since=since, max_pages=1)
    except ServiceError:
        return None
    prices = [r.price for r in records if not r.is_discounted]
    return median(prices).quantize(Decimal("0.01")) if prices else None


def lookup_barcode(code: str) -> dict | None:
    """Initial form data for a scanned product, enriched with Open Food Facts and Open Prices."""
    try:
        product = openfoodfacts.get_product(code)
    except ServiceError:
        return None
    if product is None:
        return None
    ingredient = match_ingredient(product)
    unit, quantity = Unit.PIECE, Decimal(1)
    if product.quantity_value and product.quantity_unit in {Unit.GRAM, Unit.MILLILITER}:
        unit, quantity = product.quantity_unit, Decimal(str(product.quantity_value))
    return {
        "barcode": product.code,
        "name": product.name or code,
        "brand": product.brand,
        "image_url": product.image_url,
        "nutriscore": product.nutriscore,
        "green_score": product.green_score,
        "ingredient": ingredient.pk if ingredient else None,
        "quantity": quantity,
        "unit": unit,
        "estimated_value": product_price(code),
    }


@dataclass
class WasteStats:
    in_stock: int = 0
    expiring: int = 0
    consumed: int = 0
    wasted: int = 0
    saved_value: Decimal = Decimal(0)
    wasted_value: Decimal = Decimal(0)

    @property
    def anti_waste_rate(self) -> int | None:
        closed = self.consumed + self.wasted
        return round(100 * self.consumed / closed) if closed else None


def stats_for(user, days: int = 30) -> WasteStats:
    since = timezone.localdate() - timedelta(days=days)
    items = PantryItem.objects.filter(user=user)
    status = PantryItem.Status
    closed = Q(closed_on__gte=since)
    agg = items.aggregate(
        in_stock=Count("id", filter=Q(status=status.IN_STOCK)),
        consumed=Count("id", filter=closed & Q(status=status.CONSUMED)),
        wasted=Count("id", filter=closed & Q(status=status.WASTED)),
        saved_value=Sum("estimated_value", filter=closed & Q(status=status.CONSUMED)),
        wasted_value=Sum("estimated_value", filter=closed & Q(status=status.WASTED)),
    )
    return WasteStats(
        in_stock=agg["in_stock"],
        expiring=items.expiring().count(),
        consumed=agg["consumed"],
        wasted=agg["wasted"],
        saved_value=agg["saved_value"] or Decimal(0),
        wasted_value=agg["wasted_value"] or Decimal(0),
    )


@dataclass
class Suggestion:
    recipe: Recipe
    score: float
    matched: list[RecipeIngredient] = field(default_factory=list)
    missing: list[RecipeIngredient] = field(default_factory=list)
    urgent: list[RecipeIngredient] = field(default_factory=list)

    @property
    def match_rate(self) -> int:
        total = len(self.matched) + len(self.missing)
        return round(100 * len(self.matched) / total) if total else 0


def suggest_recipes(user, limit: int = 6) -> list[Suggestion]:
    """Rank recipes by how well they use the pantry, favouring items close to expiry."""
    stock = PantryItem.objects.filter(user=user, ingredient__isnull=False).in_stock()
    weights: dict[int, int] = {}
    urgent_ids = set(stock.expiring().values_list("ingredient_id", flat=True))
    for ingredient_id in stock.values_list("ingredient_id", flat=True):
        weights[ingredient_id] = EXPIRING_WEIGHT if ingredient_id in urgent_ids else 1
    if not weights:
        return []

    candidates = (
        Recipe.objects.published()
        .with_relations()
        .filter(items__ingredient_id__in=weights.keys())
        .distinct()
    )
    suggestions = []
    for recipe in candidates:
        items = [item for item in recipe.items.all() if not item.ingredient.is_staple]
        if not items:
            continue
        suggestion = Suggestion(recipe=recipe, score=0)
        for item in items:
            weight = weights.get(item.ingredient_id)
            if weight:
                suggestion.matched.append(item)
                suggestion.score += weight
                if item.ingredient_id in urgent_ids:
                    suggestion.urgent.append(item)
            else:
                suggestion.missing.append(item)
        suggestion.score /= len(items)
        suggestions.append(suggestion)
    suggestions.sort(key=lambda s: (-s.score, len(s.missing)))
    return suggestions[:limit]
