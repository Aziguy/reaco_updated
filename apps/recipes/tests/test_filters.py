from decimal import Decimal
from itertools import product

import pytest
from django.urls import reverse

from apps.recipes.forms import SORTS
from apps.recipes.models import Diet, Ingredient, Recipe, RecipeIngredient

pytestmark = pytest.mark.django_db

LIST_URL = reverse("recipes:list")


@pytest.fixture
def catalog(db):
    """30 recipes created in one batch, so they share the same timestamp."""
    vegan = Diet.objects.create(name="Vegan", slug="vegan")
    cream = Ingredient.objects.create(name="Crème fraîche", slug="creme-fraiche")
    tomato = Ingredient.objects.create(name="Tomate", slug="tomate")
    recipes = Recipe.objects.bulk_create(
        Recipe(
            title=f"Recette {index:02d}",
            slug=f"recette-{index:02d}",
            course="dessert" if index % 3 == 0 else "main",
            difficulty=1 + index % 4,
            prep_minutes=10,
            cook_minutes=index % 5 * 10,
            cost_per_serving=Decimal(index % 4) if index % 6 else None,
            co2_per_serving=Decimal("0.5") if index % 2 else None,
        )
        for index in range(30)
    )
    for recipe in recipes[:5]:
        recipe.diets.add(vegan)
        RecipeIngredient.objects.create(recipe=recipe, ingredient=cream, quantity=100, unit="g")
        RecipeIngredient.objects.create(recipe=recipe, ingredient=tomato, quantity=100, unit="g")
    RecipeIngredient.objects.create(recipe=recipes[5], ingredient=tomato, quantity=100, unit="g")
    return recipes


def titles(response):
    return [recipe.title for recipe in response.context["page"].object_list]


@pytest.mark.parametrize("sort", ["", *SORTS])
def test_pages_cover_every_recipe_once(client, catalog, sort):
    seen = []
    for page in (1, 2, 3):
        response = client.get(LIST_URL, {"sort": sort, "page": page})
        seen += titles(response)
    assert sorted(seen) == sorted(recipe.title for recipe in catalog)


@pytest.mark.parametrize("sort, query", list(product(["", *SORTS], ["", "creme", "tomate creme"])))
def test_search_and_sort_combinations(client, catalog, sort, query):
    response = client.get(LIST_URL, {"q": query, "sort": sort})
    assert response.status_code == 200
    expected = {"": 30, "creme": 5, "tomate creme": 5}[query]
    assert response.context["page"].paginator.count == expected


def test_search_ignores_case_and_accents(client, catalog):
    for query in ("CRÈME", "creme", "Crème Fraîche", "recette 01"):
        assert client.get(LIST_URL, {"q": query}).context["page"].paginator.count >= 1


def test_combined_filters(client, catalog):
    response = client.get(
        LIST_URL, {"diet": "vegan", "course": "main", "difficulty": 3, "max_minutes": 45}
    )
    recipes = list(response.context["page"].object_list)
    assert recipes
    for recipe in recipes:
        assert recipe.course == "main"
        assert recipe.difficulty <= 3
        assert recipe.total_minutes <= 45
        assert recipe.diets.filter(slug="vegan").exists()


def test_cheap_sort_puts_unknown_costs_last(client, catalog):
    response = client.get(LIST_URL, {"sort": "cheap"})
    costs = [recipe.cost_per_serving for recipe in response.context["page"].object_list]
    known = [cost for cost in costs if cost is not None]
    assert known == sorted(known)
    assert costs[: len(known)] == known


def test_invalid_parameters_are_ignored(client, catalog):
    response = client.get(LIST_URL, {"difficulty": "abc", "sort": "nope", "page": "x"})
    assert response.status_code == 200
    assert response.context["page"].number == 1


def test_out_of_range_page_shows_last_page(client, catalog):
    assert client.get(LIST_URL, {"page": 99}).context["page"].number == 3


def test_pagination_links_keep_filters(client, catalog):
    content = client.get(LIST_URL, {"course": "main", "q": ""}).content.decode()
    assert "course=main&amp;page=2" in content
    assert "q=&amp;" not in content


def test_htmx_response_pushes_clean_url(client, catalog):
    response = client.get(LIST_URL, {"q": "", "course": "main", "sort": ""}, HTTP_HX_REQUEST="true")
    assert response["HX-Push-Url"] == f"{LIST_URL}?course=main"
    assert "<html" not in response.content.decode()


def test_active_secondary_filters_stay_visible(client, catalog):
    closed = client.get(LIST_URL).content.decode()
    opened = client.get(LIST_URL, {"diet": "vegan"}).content.decode()
    assert 'id="more-filters" class="hidden' in closed
    assert 'id="more-filters" class="hidden' not in opened


def test_api_filters_and_pagination(client, catalog):
    data = client.get("/api/v1/recipes/", {"q": "creme", "sort": "quick"}).json()
    assert data["count"] == 5
    first = client.get("/api/v1/recipes/").json()
    second = client.get(first["next"]).json()
    slugs = [r["slug"] for r in first["results"] + second["results"]]
    assert len(slugs) == len(set(slugs)) == 30


def test_search_index_follows_ingredients_and_diets(client, catalog):
    recipe = catalog[10]
    leek = Ingredient.objects.create(name="Poireau", slug="poireau")
    item = RecipeIngredient.objects.create(recipe=recipe, ingredient=leek, quantity=1, unit="piece")
    assert client.get(LIST_URL, {"q": "poireau"}).context["page"].paginator.count == 1
    item.delete()
    assert client.get(LIST_URL, {"q": "poireau"}).context["page"].paginator.count == 0
    recipe.diets.add(Diet.objects.create(name="Sans gluten", slug="sans-gluten"))
    assert client.get(LIST_URL, {"q": "sans gluten"}).context["page"].paginator.count == 1


def test_invalid_parameter_keeps_other_filters(client, catalog):
    response = client.get(LIST_URL, {"difficulty": "abc", "course": "dessert"})
    assert {recipe.course for recipe in response.context["page"].object_list} == {"dessert"}


def test_default_sort_is_not_sent(client, catalog):
    content = client.get(LIST_URL).content.decode()
    assert '<option value="" selected>Les plus récentes</option>' in content
    assert client.get(LIST_URL, {"sort": "recent"}).status_code == 200


def test_cuisine_filter(client, recipe):
    Recipe.objects.filter(pk=recipe.pk).update(cuisine=Recipe.Cuisine.INDIA)
    assert recipe.title in client.get(LIST_URL, {"cuisine": "india"}).content.decode()
    assert recipe.title not in client.get(LIST_URL, {"cuisine": "asia"}).content.decode()


def test_cuisine_is_searchable(recipe):
    recipe.cuisine = Recipe.Cuisine.AFRICA
    recipe.save()
    assert "afrique" in recipe.search_text


def test_home_lists_world_cuisines(client, recipe):
    Recipe.objects.filter(pk=recipe.pk).update(cuisine=Recipe.Cuisine.ASIA)
    content = client.get(reverse("core:home")).content.decode()
    assert "Cuisines du monde" in content and "?cuisine=asia" in content


def test_vegetarian_filter_includes_vegan_recipes(client, recipe):
    Diet.objects.create(name="Végétarien", slug="vegetarien")
    recipe.diets.add(Diet.objects.create(name="Vegan", slug="vegan"))
    content = client.get(LIST_URL, {"diet": "vegetarien"}).content.decode()
    assert recipe.title in content
    assert list(Recipe.objects.for_diet("vegetarien")) == [recipe]
