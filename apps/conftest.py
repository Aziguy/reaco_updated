from datetime import date, timedelta
from decimal import Decimal

import pytest
import respx
from django.core.cache import cache

from apps.pricing.models import PriceObservation, Store
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient, RecipeStep


@pytest.fixture(autouse=True)
def _isolation(settings, tmp_path):
    """Clear cache, isolate media and answer unmocked HTTP calls with an empty body."""
    cache.clear()
    settings.MEDIA_ROOT = tmp_path
    with respx.mock(assert_all_called=False, assert_all_mocked=False) as router:
        yield router


@pytest.fixture
def http(_isolation):
    return _isolation


@pytest.fixture
def user(django_user_model):
    return django_user_model.objects.create_user(
        email="alice@example.com", password="secret-pass-123", household_size=2
    )


@pytest.fixture
def other_user(django_user_model):
    return django_user_model.objects.create_user(email="bob@example.com", password="x")


@pytest.fixture
def auth_client(client, user):
    client.force_login(user)
    return client


@pytest.fixture
def ingredients(db):
    return {
        "tomate": Ingredient.objects.create(
            name="Tomate",
            aisle="produce",
            price_unit="kg",
            unit_weight_g=Decimal(120),
            off_category="en:tomatoes",
            impactco2_slug="tomate",
        ),
        "oeuf": Ingredient.objects.create(
            name="Œuf", aisle="dairy", price_unit="unit", unit_weight_g=Decimal(60)
        ),
        "lait": Ingredient.objects.create(name="Lait", aisle="dairy", price_unit="l"),
        "sel": Ingredient.objects.create(name="Sel", aisle="spices", is_staple=True),
    }


@pytest.fixture
def recipe(ingredients):
    recipe = Recipe.objects.create(title="Omelette tomate", servings=2, prep_minutes=5)
    RecipeIngredient.objects.create(
        recipe=recipe, ingredient=ingredients["tomate"], quantity=Decimal(250), unit="g"
    )
    RecipeIngredient.objects.create(
        recipe=recipe, ingredient=ingredients["oeuf"], quantity=Decimal(4), unit="piece"
    )
    RecipeIngredient.objects.create(
        recipe=recipe, ingredient=ingredients["sel"], quantity=Decimal(1), unit="pinch"
    )
    RecipeStep.objects.create(recipe=recipe, position=1, text="Battre les œufs.")
    return recipe


@pytest.fixture
def stores(db):
    return {
        "cheap": Store.objects.create(
            osm_type="NODE", osm_id=1, name="Discount Toulon", brand="Discount",
            latitude=43.12, longitude=5.93,
        ),
        "fancy": Store.objects.create(
            osm_type="NODE", osm_id=2, name="Premium Lyon", brand="Premium",
            latitude=45.76, longitude=4.83,
        ),
    }  # fmt: skip


@pytest.fixture
def prices(ingredients, stores):
    today = date.today()
    rows = [
        (ingredients["tomate"], stores["cheap"], "2.00", "kg"),
        (ingredients["tomate"], stores["fancy"], "4.00", "kg"),
        (ingredients["oeuf"], stores["cheap"], "0.25", "unit"),
        (ingredients["oeuf"], stores["fancy"], "0.45", "unit"),
    ]
    return [
        PriceObservation.objects.create(
            source_id=index,
            ingredient=ingredient,
            store=store,
            price=Decimal(price),
            unit_price=Decimal(price),
            base_unit=unit,
            observed_on=today - timedelta(days=index),
        )
        for index, (ingredient, store, price, unit) in enumerate(rows, start=1)
    ]
