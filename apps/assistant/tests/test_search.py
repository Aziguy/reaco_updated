from decimal import Decimal

import pytest
from django.urls import reverse

from apps.assistant.models import Mode
from apps.assistant.search import Criteria, apply, guess, interpret
from apps.assistant.services import Caller
from apps.recipes.models import Diet, Recipe

pytestmark = pytest.mark.django_db

REPLY = {
    "ingredients": ["tomates", "truffe"],
    "excluded": [],
    "keywords": "",
    "course": "",
    "diet": "",
    "max_minutes": 30,
    "max_cost": 4.5,
    "sort": "cheap",
    "use_pantry": False,
    "servings": 2,
    "summary": "Un plat rapide avec des tomates.",
}


def caller(user=None):
    return Caller(user, "1.2.3.4")


@pytest.fixture
def vegetarian(recipe):
    diet = Diet.objects.create(name="Végétarien", slug="vegetarien")
    recipe.diets.add(diet)
    return diet


def test_interpret_resolves_ingredients_and_caches(fake_ai, recipe):
    fake_ai.reply(REPLY)
    criteria, notice = interpret("Un truc rapide avec des tomates", Mode.FAST, caller())
    assert notice == ""
    assert criteria.ingredients == ["tomate"]
    assert criteria.unknown == ["truffe"]
    assert (criteria.max_minutes, criteria.max_cost, criteria.servings) == (30, "4.50", 2)
    again, _ = interpret("un truc RAPIDE avec des tomates", Mode.FAST, caller())
    assert again.ingredients == ["tomate"]
    assert len(fake_ai.prompts) == 1
    assert "Tomate" in fake_ai.prompts[0].system


def test_interpret_ignores_values_outside_the_schema(fake_ai, recipe):
    fake_ai.reply({**REPLY, "course": "pizza", "diet": "keto", "sort": "random", "max_cost": -3})
    criteria, _ = interpret("n'importe quoi", Mode.FAST, caller())
    assert (criteria.course, criteria.diet, criteria.sort, criteria.max_cost) == ("", "", "", "")


def test_interpret_falls_back_to_rough_parser(ai_config, monkeypatch, recipe, vegetarian):
    monkeypatch.delenv("TEST_AI_KEY")
    criteria, notice = interpret("Un dîner végé pour 2 avec des tomates, 8 €", Mode.FAST, caller())
    assert "indisponible" in notice
    assert criteria.ingredients == ["tomate"]
    assert (criteria.diet, criteria.servings, criteria.max_cost) == ("vegetarien", 2, "4.00")


def test_guess_reads_time_and_pantry():
    data = guess("Quelque chose de rapide avec les restes du frigo")
    assert data["max_minutes"] == 30 and data["use_pantry"] is True


def test_apply_relaxes_budget_but_never_the_diet(recipe, vegetarian):
    Recipe.objects.filter(pk=recipe.pk).update(cost_per_serving=Decimal("3.00"))
    recipes, relaxed = apply(Criteria(ingredients=["tomate"], max_cost="1.00"))
    assert recipes == [recipe] and relaxed == ["le budget"]
    recipes, _ = apply(Criteria(ingredients=["tomate"], diet="vegan"))
    assert recipes == []


def test_apply_excludes_ingredients(recipe):
    assert apply(Criteria(excluded=["oeuf"]))[0] == []
    assert apply(Criteria(ingredients=["tomate", "lait"]))[0] == [recipe]


def test_apply_ranks_pantry_matches_first(recipe, user, ingredients):
    other = Recipe.objects.create(title="Lait chaud", servings=1)
    other.items.create(ingredient=ingredients["lait"], quantity=Decimal(200), unit="ml")
    user.pantry_items.create(name="Œufs", ingredient=ingredients["oeuf"])
    recipes, _ = apply(Criteria(use_pantry=True), user)
    assert recipes[0] == recipe


def test_criteria_token_round_trip_and_tampering():
    criteria = Criteria(text="soupe", keywords="soupe", max_minutes=20)
    assert Criteria.from_token(criteria.token) == criteria
    assert Criteria.from_token(criteria.token + "x") is None


def test_chips_remove_one_criterion(recipe, vegetarian):
    criteria = Criteria(ingredients=["tomate"], diet="vegetarien", max_minutes=20)
    chips = {chip.label: Criteria.from_token(chip.token) for chip in criteria.chips()}
    assert set(chips) == {"Tomate", "Végétarien", "20 min max."}
    assert chips["Tomate"].ingredients == [] and chips["Tomate"].diet == "vegetarien"


def test_search_page_loads_results_lazily(client, fake_ai, recipe):
    url = reverse("assistant:search")
    page = client.get(url, {"demande": "tomates"})
    assert page.status_code == 200 and 'hx-trigger="load"' in page.content.decode()
    assert fake_ai.prompts == []

    fake_ai.reply(REPLY)
    partial = client.get(url, {"demande": "tomates"}, headers={"HX-Request": "true"})
    content = partial.content.decode()
    assert "Un plat rapide avec des tomates." in content
    assert recipe.title in content
    assert "c=" in partial["HX-Replace-Url"]


def test_search_with_token_needs_no_model(client, fake_ai, recipe):
    token = Criteria(text="omelette", ingredients=["tomate"]).token
    response = client.get(reverse("assistant:search"), {"demande": "omelette", "c": token})
    assert recipe.title in response.content.decode()
    assert fake_ai.prompts == []


def test_search_bar_on_home_and_recipes(client, db):
    for name in ("core:home", "recipes:list"):
        assert reverse("assistant:search") in client.get(reverse(name)).content.decode()
