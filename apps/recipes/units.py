from decimal import Decimal

from django.db import models


class Unit(models.TextChoices):
    GRAM = "g", "g"
    KILOGRAM = "kg", "kg"
    MILLILITER = "ml", "ml"
    CENTILITER = "cl", "cl"
    LITER = "l", "l"
    PIECE = "piece", "pièce"
    TABLESPOON = "tbsp", "c. à soupe"
    TEASPOON = "tsp", "c. à café"
    PINCH = "pinch", "pincée"


PLURALS = {"piece": "pièces", "pinch": "pincées"}


def unit_label(unit: str, quantity) -> str:
    """Unit label agreeing with the quantity: 1 pièce, 2 pièces."""
    if unit in PLURALS:
        return (
            PLURALS[unit] if quantity is not None and Decimal(quantity) >= 2 else Unit(unit).label
        )
    return Unit(unit).label if unit in Unit.values else ""


class BaseUnit(models.TextChoices):
    KILOGRAM = "kg", "au kilo"
    LITER = "l", "au litre"
    UNIT = "unit", "à l'unité"


MASS_KG = {Unit.GRAM: Decimal("0.001"), Unit.KILOGRAM: Decimal(1)}
VOLUME_L = {
    Unit.MILLILITER: Decimal("0.001"),
    Unit.CENTILITER: Decimal("0.01"),
    Unit.LITER: Decimal(1),
}
SPOON_KG = {
    Unit.TABLESPOON: Decimal("0.015"),
    Unit.TEASPOON: Decimal("0.005"),
    Unit.PINCH: Decimal("0.0005"),
}


def to_kilograms(quantity: Decimal, unit: str, unit_weight_g: Decimal | None) -> Decimal | None:
    """Mass in kg, assuming a density of 1 for liquids and spoons."""
    if unit in MASS_KG:
        return quantity * MASS_KG[unit]
    if unit in VOLUME_L:
        return quantity * VOLUME_L[unit]
    if unit in SPOON_KG:
        return quantity * SPOON_KG[unit]
    if unit == Unit.PIECE and unit_weight_g:
        return quantity * unit_weight_g / 1000
    return None


def to_base(quantity, unit: str, base_unit: str, unit_weight_g=None) -> Decimal | None:
    """Convert a recipe quantity into the base unit used for prices."""
    if quantity is None:
        return None
    quantity = Decimal(quantity)
    if base_unit == BaseUnit.UNIT:
        if unit == Unit.PIECE:
            return quantity
        kg = to_kilograms(quantity, unit, None)
        return kg * 1000 / unit_weight_g if kg is not None and unit_weight_g else None
    return to_kilograms(quantity, unit, unit_weight_g)


def convert_unit_price(price: Decimal, from_unit: str, to_unit: str, unit_weight_g=None):
    """Convert a price per from_unit into a price per to_unit (density 1 between kg and l)."""
    if from_unit == to_unit:
        return price
    weighted = {BaseUnit.KILOGRAM, BaseUnit.LITER}
    if from_unit in weighted and to_unit in weighted:
        return price
    if not unit_weight_g:
        return None
    piece_kg = Decimal(unit_weight_g) / 1000
    if from_unit == BaseUnit.UNIT:
        return price / piece_kg
    return price * piece_kg


def format_quantity(quantity: Decimal | None) -> str:
    if quantity is None:
        return ""
    quantity = Decimal(quantity)
    if quantity >= 10:
        quantity = quantity.quantize(Decimal(1))
    else:
        quantity = quantity.quantize(Decimal("0.01")).normalize()
    text = format(quantity, "f")
    return text.replace(".", ",")
