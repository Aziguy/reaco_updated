from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.urls import reverse

from apps.recipes import metrics
from apps.recipes.models import Favorite, Ingredient, Recipe, RecipeIngredient
from apps.recipes.units import convert_unit_price, format_quantity, to_base, unit_label


class TestUnits:
    def test_mass_and_volume(self):
        assert to_base(250, "g", "kg") == Decimal("0.250")
        assert to_base(50, "cl", "l") == Decimal("0.50")
        assert to_base(2, "tbsp", "l") == Decimal("0.030")

    def test_pieces_need_a_weight_for_mass(self):
        assert to_base(2, "piece", "kg", Decimal(120)) == Decimal("0.24")
        assert to_base(2, "piece", "kg") is None

    def test_mass_to_pieces(self):
        assert to_base(240, "g", "unit", Decimal(60)) == Decimal(4)
        assert to_base(3, "piece", "unit") == Decimal(3)

    def test_convert_unit_price(self):
        assert convert_unit_price(Decimal(5), "kg", "l") == Decimal(5)
        assert convert_unit_price(Decimal("0.30"), "unit", "kg", Decimal(60)) == Decimal(5)
        assert convert_unit_price(Decimal(5), "kg", "unit", Decimal(60)) == Decimal("0.300")
        assert convert_unit_price(Decimal(5), "kg", "unit") is None

    @pytest.mark.parametrize(
        "value, expected", [(Decimal("0.5"), "0,5"), (Decimal(2), "2"), (Decimal("12.4"), "12")]
    )
    def test_format_quantity(self, value, expected):
        assert format_quantity(value) == expected


def test_slug_handles_ligatures(ingredients):
    assert ingredients["oeuf"].slug == "oeuf"


def test_metrics_refresh(recipe, prices, http):
    http.get("https://impactco2.fr/api/v1/fruitsetlegumes").respond(
        json={"data": [{"name": "Tomate", "slug": "tomate", "months": [8], "ecv": 0.8}]}
    )
    http.get("https://impactco2.fr/api/v1/alimentation").respond(json={"data": []})
    metrics.refresh(recipe)
    recipe.refresh_from_db()
    # 0.25 kg x 3 EUR median + 4 eggs x 0.35 EUR median, for 2 servings
    assert recipe.cost_per_serving == Decimal("1.08")
    assert recipe.co2_per_serving == Decimal("0.100")
    assert recipe.price_coverage == 67


@pytest.mark.django_db
class TestViews:
    def test_list_filters(self, client, recipe):
        response = client.get(reverse("recipes:list"), {"q": "omelette"})
        assert response.status_code == 200
        assert recipe.title in response.content.decode()
        response = client.get(reverse("recipes:list"), {"q": "couscous"})
        assert "Aucune recette" in response.content.decode()

    def test_list_htmx_returns_partial(self, client, recipe):
        response = client.get(reverse("recipes:list"), HTTP_HX_REQUEST="true")
        assert "<html" not in response.content.decode()

    def test_detail_scales_servings(self, client, recipe):
        response = client.get(recipe.get_absolute_url(), {"servings": 4})
        content = response.content.decode()
        assert "500 g" in content
        assert "8 pièces" in content

    def test_unpublished_recipe_is_hidden(self, client, recipe):
        recipe.is_published = False
        recipe.save()
        assert client.get(recipe.get_absolute_url()).status_code == 404

    def test_prices_panel(self, client, recipe, prices):
        response = client.get(reverse("recipes:prices", args=[recipe.slug]))
        content = response.content.decode()
        assert "Discount" in content
        assert "le moins cher" in content

    def test_favorite_toggle(self, auth_client, user, recipe):
        url = reverse("recipes:favorite", args=[recipe.slug])
        auth_client.post(url)
        assert Favorite.objects.filter(user=user, recipe=recipe).exists()
        auth_client.post(url)
        assert not Favorite.objects.filter(user=user, recipe=recipe).exists()

    def test_favorite_requires_login(self, client, recipe):
        response = client.post(reverse("recipes:favorite", args=[recipe.slug]))
        assert response.status_code == 302


@pytest.mark.django_db
def test_seed_demo_loads_credited_images():
    call_command("seed_demo", stdout=StringIO())
    assert Recipe.objects.count() >= 30
    photo = Recipe.objects.get(slug="ratatouille")
    assert photo.image_license.startswith("CC")
    assert photo.image_source.startswith("https://commons.wikimedia.org/")
    drawing = Recipe.objects.get(slug="dahl-de-lentilles-corail")
    assert drawing.image.name.endswith(".svg")
    assert drawing.image_credit == "Illustration Comégusto"
    assert drawing.kcal and drawing.nutrition_coverage == 100
    call_command("seed_demo", stdout=StringIO())
    assert Recipe.objects.filter(slug="ratatouille").count() == 1
    assert RecipeIngredient.objects.filter(recipe=photo).count() == 8


@pytest.mark.django_db
def test_credits_page(client, recipe):
    recipe.image_credit = "Jane Doe"
    recipe.image_license = "CC BY 4.0"
    recipe.save()
    assert "Jane Doe" in client.get(reverse("core:credits")).content.decode()


def test_recipe_nutrition_per_serving(recipe, ingredients):
    Ingredient.objects.filter(pk=ingredients["tomate"].pk).update(
        kcal_100g=20, proteins_100g=1, fat_100g=0, carbs_100g=4
    )
    Ingredient.objects.filter(pk=ingredients["oeuf"].pk).update(
        kcal_100g=140, proteins_100g=12.8, fat_100g=9.8, carbs_100g=0
    )
    recipe = Recipe.objects.with_relations().get(pk=recipe.pk)
    nutrition, coverage = metrics.recipe_nutrition(recipe)
    # 250 g tomatoes (50 kcal) + 4 eggs of 60 g (336 kcal), salt not covered, 2 servings
    assert nutrition == {"kcal": 193, "proteins_g": 17, "fat_g": 12, "carbs_g": 5}
    assert coverage == 67


def test_recipe_nutrition_without_data(recipe):
    assert metrics.recipe_nutrition(Recipe.objects.with_relations().get(pk=recipe.pk)) == (None, 0)


def test_nutrition_block(client, recipe):
    Recipe.objects.filter(pk=recipe.pk).update(kcal=193, proteins_g=17, fat_g=12, carbs_g=5)
    content = client.get(recipe.get_absolute_url()).content.decode()
    assert "193 kcal" in content
    assert "Ciqual" in content


@pytest.mark.parametrize(
    "unit, quantity, expected",
    [("piece", 1, "pièce"), ("piece", Decimal("0.5"), "pièce"), ("piece", 2, "pièces"),
     ("pinch", 3, "pincées"), ("tbsp", 2, "c. à soupe"), ("g", 200, "g")],
)  # fmt: skip
def test_unit_label(unit, quantity, expected):
    assert unit_label(unit, quantity) == expected
