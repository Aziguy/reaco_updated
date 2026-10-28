from collections import defaultdict
from dataclasses import dataclass
from decimal import ROUND_CEILING, Decimal

from django.db import transaction

from apps.pantry.models import PantryItem
from apps.pricing.estimator import Line
from apps.recipes.models import Recipe
from apps.recipes.units import Unit, to_base

from .models import ShoppingItem, ShoppingList


@dataclass
class AddResult:
    added: int = 0
    merged: int = 0
    in_pantry: int = 0


def pantry_stock(user) -> dict[int, list[PantryItem]]:
    stock = defaultdict(list)
    items = PantryItem.objects.filter(user=user, ingredient__isnull=False).in_stock()
    for item in items.select_related("ingredient"):
        stock[item.ingredient_id].append(item)
    return stock


def _available(ingredient, items: list[PantryItem]) -> Decimal | None:
    """Pantry quantity expressed in the ingredient price unit, None if unknown."""
    total = Decimal(0)
    for item in items:
        amount = to_base(item.quantity, item.unit, ingredient.price_unit, ingredient.unit_weight_g)
        if amount is None:
            return None
        total += amount
    return total


def _rounded(quantity: Decimal | None, unit: str) -> Decimal | None:
    if quantity is None:
        return None
    if unit == Unit.PIECE:
        return quantity.to_integral_value(rounding=ROUND_CEILING)
    return quantity.quantize(Decimal("0.01"))


@transaction.atomic
def add_recipe(
    shopping_list: ShoppingList,
    recipe: Recipe,
    servings: int,
    *,
    use_pantry: bool = True,
    have: frozenset[int] = frozenset(),
) -> AddResult:
    """Add the recipe ingredients, minus staples, `have` ingredients and pantry stock."""
    result = AddResult()
    factor = Decimal(servings) / recipe.servings
    stock = pantry_stock(shopping_list.user) if use_pantry else {}
    existing = {
        (item.ingredient_id, item.unit): item
        for item in shopping_list.items.filter(ingredient__isnull=False, is_checked=False)
    }

    for entry in recipe.items.select_related("ingredient"):
        ingredient = entry.ingredient
        if ingredient.is_staple:
            continue
        if ingredient.pk in have:
            result.in_pantry += 1
            continue
        quantity = entry.scaled(factor)
        if ingredient.pk in stock:
            available = _available(ingredient, stock[ingredient.pk])
            needed = to_base(quantity, entry.unit, ingredient.price_unit, ingredient.unit_weight_g)
            if available is None or needed is None or available >= needed:
                result.in_pantry += 1
                continue
            quantity = quantity * (needed - available) / needed

        item = existing.get((ingredient.pk, entry.unit))
        if item:
            if item.quantity is not None and quantity is not None:
                item.quantity = _rounded(item.quantity + quantity, entry.unit)
                item.save(update_fields=["quantity"])
            result.merged += 1
        else:
            item = ShoppingItem.objects.create(
                shopping_list=shopping_list,
                ingredient=ingredient,
                label=ingredient.name,
                quantity=_rounded(quantity, entry.unit),
                unit=entry.unit,
            )
            existing[(ingredient.pk, entry.unit)] = item
            result.added += 1
        item.recipes.add(recipe)

    shopping_list.save(update_fields=["updated_at"])
    return result


def basket_lines(shopping_list: ShoppingList) -> list[Line]:
    items = shopping_list.items.filter(ingredient__isnull=False, is_checked=False)
    return [
        Line(item.ingredient, item.quantity, item.unit)
        for item in items.select_related("ingredient")
    ]
