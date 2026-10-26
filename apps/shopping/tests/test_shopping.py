from decimal import Decimal

import pytest
from django.urls import reverse

from apps.pantry.models import PantryItem
from apps.shopping.models import ShoppingItem, ShoppingList
from apps.shopping.services import add_recipe


@pytest.fixture
def shopping_list(user):
    return ShoppingList.objects.create(user=user, name="Semaine")


def quantities(shopping_list):
    return {i.ingredient.slug: i.quantity for i in shopping_list.items.select_related("ingredient")}


class TestAddRecipe:
    def test_scales_and_merges(self, shopping_list, recipe):
        add_recipe(shopping_list, recipe, servings=4)
        result = add_recipe(shopping_list, recipe, servings=2)
        assert result.merged == 2
        assert quantities(shopping_list) == {"tomate": Decimal(750), "oeuf": Decimal(12)}

    def test_rounds_pieces_up(self, shopping_list, recipe):
        add_recipe(shopping_list, recipe, servings=1)
        assert quantities(shopping_list)["oeuf"] == Decimal(2)
        add_recipe(shopping_list, recipe, servings=1)
        assert quantities(shopping_list)["oeuf"] == Decimal(4)

    def test_deducts_pantry_stock(self, shopping_list, recipe, ingredients, user):
        PantryItem.objects.create(
            user=user, name="Œufs", ingredient=ingredients["oeuf"], quantity=1, unit="piece"
        )
        result = add_recipe(shopping_list, recipe, servings=2)
        assert result.in_pantry == 0
        assert quantities(shopping_list) == {"tomate": Decimal(250), "oeuf": Decimal(3)}

    def test_skips_items_fully_in_stock(self, shopping_list, recipe, ingredients, user):
        PantryItem.objects.create(
            user=user, name="Tomates", ingredient=ingredients["tomate"], quantity=1, unit="kg"
        )
        result = add_recipe(shopping_list, recipe, servings=2)
        assert result.in_pantry == 1
        assert "tomate" not in quantities(shopping_list)

    def test_ignores_pantry_when_asked(self, shopping_list, recipe, ingredients, user):
        PantryItem.objects.create(
            user=user, name="Tomates", ingredient=ingredients["tomate"], quantity=1, unit="kg"
        )
        add_recipe(shopping_list, recipe, servings=2, use_pantry=False)
        assert "tomate" in quantities(shopping_list)


@pytest.mark.django_db
class TestViews:
    def test_add_recipe_creates_list(self, auth_client, user, recipe):
        response = auth_client.post(
            reverse("shopping:add_recipe"), {"recipe": recipe.pk, "servings": 2}
        )
        shopping_list = user.shopping_lists.get()
        assert response.url == shopping_list.get_absolute_url()
        assert shopping_list.items.count() == 2

    def test_toggle_and_checkout(self, auth_client, user, shopping_list, ingredients):
        item = ShoppingItem.objects.create(
            shopping_list=shopping_list, ingredient=ingredients["lait"], label="Lait", unit="l"
        )
        response = auth_client.post(
            reverse("shopping:toggle_item", args=[item.pk]), HTTP_HX_REQUEST="true"
        )
        assert response["HX-Trigger"] == "shopping-changed"
        auth_client.post(reverse("shopping:checkout", args=[shopping_list.pk]))
        assert not shopping_list.items.exists()
        assert user.pantry_items.get().ingredient == ingredients["lait"]

    def test_compare_panel(self, auth_client, shopping_list, ingredients, prices):
        ShoppingItem.objects.create(
            shopping_list=shopping_list,
            ingredient=ingredients["tomate"],
            label="Tomate",
            quantity=1,
            unit="kg",
        )
        response = auth_client.get(reverse("shopping:compare", args=[shopping_list.pk]))
        assert "Discount" in response.content.decode()

    def test_lists_are_private(self, client, other_user, shopping_list):
        client.force_login(other_user)
        assert client.get(shopping_list.get_absolute_url()).status_code == 404
        assert client.post(reverse("shopping:delete", args=[shopping_list.pk])).status_code == 404
