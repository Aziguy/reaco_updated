import pytest

from apps.pantry.models import PantryItem
from apps.shopping.models import ShoppingList


@pytest.mark.django_db
class TestRecipes:
    def test_list_and_detail(self, client, recipe):
        data = client.get("/api/v1/recipes/").json()
        assert data["count"] == 1
        detail = client.get(f"/api/v1/recipes/{recipe.slug}/").json()
        assert detail["steps"] == ["Battre les œufs."]
        assert len(detail["items"]) == 3

    def test_estimate(self, client, recipe, prices):
        data = client.get(f"/api/v1/recipes/{recipe.slug}/estimate/", {"servings": 4}).json()
        assert data["total"] == "4.30"
        assert data["offers"][0]["brand"] == "Discount"

    def test_estimate_near(self, client, recipe, prices):
        params = {"lat": 43.12, "lon": 5.93, "radius_km": 5}
        data = client.get(f"/api/v1/recipes/{recipe.slug}/estimate/", params).json()
        assert [offer["brand"] for offer in data["offers"]] == ["Discount"]

    def test_read_only(self, auth_client, recipe):
        assert auth_client.delete(f"/api/v1/recipes/{recipe.slug}/").status_code == 405


@pytest.mark.django_db
class TestPrivateResources:
    def test_auth_required(self, client):
        assert client.get("/api/v1/pantry/").status_code in {401, 403}

    def test_pantry_is_scoped_to_user(self, auth_client, user, other_user):
        PantryItem.objects.create(user=other_user, name="Secret")
        response = auth_client.post(
            "/api/v1/pantry/", {"name": "Lait", "unit": "l"}, content_type="application/json"
        )
        assert response.status_code == 201
        names = [item["name"] for item in auth_client.get("/api/v1/pantry/").json()["results"]]
        assert names == ["Lait"]

    def test_add_recipe_to_list(self, auth_client, user, recipe):
        shopping_list = ShoppingList.objects.create(user=user)
        response = auth_client.post(
            f"/api/v1/shopping-lists/{shopping_list.pk}/add-recipe/",
            {"recipe": recipe.slug, "servings": 2},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2


@pytest.mark.django_db
def test_schema(client):
    assert client.get("/api/schema/").status_code == 200
