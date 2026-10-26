from decimal import Decimal

from django.utils import timezone

from apps.integrations.impactco2 import safe_food_footprints

from .models import Recipe
from .units import to_kilograms


def basket_lines(recipe: Recipe, servings: int | None = None):
    from apps.pricing.estimator import Line

    factor = Decimal(servings or recipe.servings) / recipe.servings
    return [Line(item.ingredient, item.scaled(factor), item.unit) for item in recipe.items.all()]


def recipe_co2(recipe: Recipe, footprints: dict[str, Decimal]) -> Decimal | None:
    total, known = Decimal(0), False
    for item in recipe.items.all():
        factor = footprints.get(item.ingredient.impactco2_slug)
        if factor is None or item.quantity is None:
            continue
        kg = to_kilograms(item.quantity, item.unit, item.ingredient.unit_weight_g)
        if kg is not None:
            total += kg * factor
            known = True
    return total if known else None


NUTRIENTS = {
    "kcal": "kcal_100g",
    "proteins_g": "proteins_100g",
    "fat_g": "fat_100g",
    "carbs_g": "carbs_100g",
}


def recipe_nutrition(recipe: Recipe) -> tuple[dict[str, int] | None, int]:
    """Per serving nutrients from Ciqual values, and the share of ingredients covered (%)."""
    totals = dict.fromkeys(NUTRIENTS, Decimal(0))
    counted = covered = 0
    for item in recipe.items.all():
        if item.quantity is None:
            continue
        counted += 1
        ingredient = item.ingredient
        kg = to_kilograms(item.quantity, item.unit, ingredient.unit_weight_g)
        if kg is None or ingredient.kcal_100g is None:
            continue
        covered += 1
        for field, source in NUTRIENTS.items():
            totals[field] += kg * 10 * (getattr(ingredient, source) or 0)
    coverage = round(100 * covered / counted) if counted else 0
    if not covered:
        return None, coverage
    return {field: round(total / recipe.servings) for field, total in totals.items()}, coverage


def refresh(recipe: Recipe, footprints: dict[str, Decimal] | None = None) -> Recipe:
    from apps.pricing.estimator import estimate

    footprints = safe_food_footprints() if footprints is None else footprints
    basket = estimate(basket_lines(recipe))
    servings = Decimal(recipe.servings)
    recipe.cost_per_serving = (
        (basket.total / servings).quantize(Decimal("0.01")) if basket.total else None
    )
    recipe.price_coverage = basket.coverage
    co2 = recipe_co2(recipe, footprints)
    recipe.co2_per_serving = (
        (co2 / servings).quantize(Decimal("0.001")) if co2 is not None else None
    )
    nutrition, recipe.nutrition_coverage = recipe_nutrition(recipe)
    for field in NUTRIENTS:
        setattr(recipe, field, nutrition[field] if nutrition else None)
    recipe.metrics_updated_at = timezone.now()
    recipe.save(
        update_fields=[
            "cost_per_serving",
            "price_coverage",
            "co2_per_serving",
            *NUTRIENTS,
            "nutrition_coverage",
            "metrics_updated_at",
        ]
    )
    return recipe


def refresh_all() -> int:
    footprints = safe_food_footprints()
    recipes = Recipe.objects.with_relations()
    for recipe in recipes:
        refresh(recipe, footprints)
    return len(recipes)
