import io
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.assistant import planner
from apps.assistant.models import MealPlan, Mode
from apps.assistant.services import Caller
from apps.pantry.models import PantryItem
from apps.recipes.models import Recipe

pytestmark = pytest.mark.django_db


@pytest.fixture
def menu(recipe, ingredients):
    soup = Recipe.objects.create(title="Soupe de lait", course="soup", servings=2)
    soup.items.create(ingredient=ingredients["lait"], quantity=Decimal(500), unit="ml")
    salad = Recipe.objects.create(title="Salade de tomates", course="salad", servings=2)
    salad.items.create(ingredient=ingredients["tomate"], quantity=Decimal(300), unit="g")
    flan = Recipe.objects.create(title="Flan", course="main", servings=2)
    flan.items.create(ingredient=ingredients["oeuf"], quantity=Decimal(3), unit="piece")
    Recipe.objects.filter(pk=recipe.pk).update(cost_per_serving=Decimal("2.00"))
    return [recipe, soup, salad, flan]


@pytest.fixture
def plan(user, menu):
    return MealPlan.objects.create(user=user, days=3, servings=2)


def test_plan_uses_model_choices_and_fills_gaps(fake_ai, plan, menu, user, ingredients):
    user.pantry_items.create(
        name="Tomates", ingredient=ingredients["tomate"],
        expires_on=timezone.localdate() + timedelta(days=1),
    )  # fmt: skip
    fake_ai.reply(
        {
            "meals": [
                {
                    "day": 1,
                    "slot": "dinner",
                    "recipe_id": menu[0].pk,
                    "reason": "Sauve vos tomates.",
                },
                {"day": 2, "slot": "dinner", "recipe_id": 999999, "reason": "Inventée"},
                {"day": 9, "slot": "dinner", "recipe_id": menu[1].pk, "reason": "Hors menu"},
            ],
            "summary": "Un menu doux.",
            "tips": ["Gardez le bouillon."],
        }
    )
    plan = planner.generate(plan, Caller(user, ""))
    meals = list(plan.meals.all())
    assert plan.status == MealPlan.Status.READY and not plan.is_fallback
    assert [meal.day for meal in meals] == [1, 2, 3]
    assert meals[0].reason == "Sauve vos tomates."
    assert len({meal.recipe_id for meal in meals}) == 3
    assert "tomate" in fake_ai.prompts[0].text.lower() and " !" in fake_ai.prompts[0].text
    totals = planner.totals(plan, meals)
    assert totals.saved == ["Tomate"]


def test_plan_without_assistant_is_still_composed(ai_config, monkeypatch, plan, user):
    monkeypatch.delenv("TEST_AI_KEY")
    plan = planner.generate(plan, Caller(user, ""))
    assert plan.is_fallback and plan.meals.count() == 3
    assert "automatiquement" in plan.summary


def test_plan_runs_once(fake_ai, plan, user):
    fake_ai.reply({"meals": [], "summary": "", "tips": []})
    planner.generate(plan, Caller(user, ""))
    planner.generate(plan, Caller(user, ""))
    assert len(fake_ai.prompts) == 1


def test_plan_pages(auth_client, fake_ai, menu, user, other_user):
    response = auth_client.post(
        reverse("assistant:plan_new"),
        {"days": 3, "meals_per_day": 1, "servings": 2, "use_pantry": "on", "mode": Mode.FAST},
    )
    plan = MealPlan.objects.get()
    assert response.url == plan.get_absolute_url()
    assert 'hx-trigger="load"' in auth_client.get(response.url).content.decode()

    fake_ai.reply({"meals": [], "summary": "Prêt !", "tips": []})
    content = auth_client.post(reverse("assistant:plan_run", args=[plan.pk])).content.decode()
    assert "Prêt !" in content and "Créer la liste de courses" in content

    meal = plan.meals.first()
    auth_client.post(reverse("assistant:meal_swap", args=[plan.pk, meal.pk]))
    meal.refresh_from_db()
    assert meal.recipe not in [m.recipe for m in plan.meals.exclude(pk=meal.pk)]

    response = auth_client.post(reverse("assistant:plan_shopping", args=[plan.pk]))
    plan.refresh_from_db()
    assert response.url == plan.shopping_list.get_absolute_url()
    assert plan.shopping_list.items.exists()

    auth_client.force_login(other_user)
    assert auth_client.get(plan.get_absolute_url()).status_code == 404


def test_planner_requires_login(client):
    response = client.get(reverse("assistant:plan_new"))
    assert response.status_code == 302 and "/compte/login/" in response.url


RECIPE = {
    "title": "Omelette du frigo",
    "summary": "Fondante.",
    "course": "main",
    "difficulty": 1,
    "prep_minutes": 5,
    "cook_minutes": 10,
    "ingredients": [
        {"name": "Tomates", "quantity": 200, "unit": "g", "note": "en dés"},
        {"name": "oeuf", "quantity": 3, "unit": "piece", "note": ""},
        {"name": "Sel", "quantity": 1, "unit": "pinch", "note": ""},
        {"name": "Caviar", "quantity": 10, "unit": "g", "note": ""},
    ],
    "steps": ["Battre les œufs.", "Cuire."],
}


@pytest.fixture
def stock(user, ingredients):
    return user.pantry_items.create(name="Tomates", ingredient=ingredients["tomate"])


def test_fridge_creates_private_recipe(auth_client, fake_ai, stock, user, client, other_user):
    fake_ai.reply(RECIPE)
    response = auth_client.post(
        reverse("assistant:fridge"),
        {"products": [stock.pk], "servings": 2, "wishes": "", "mode": Mode.FAST},
    )
    recipe = Recipe.objects.get(slug="omelette-du-frigo")
    assert response.url.startswith(recipe.get_absolute_url())
    assert recipe.author == user and recipe.is_ai_generated and not recipe.is_published
    assert [i.ingredient.slug for i in recipe.items.all()] == ["tomate", "oeuf", "sel"]
    assert recipe.steps.count() == 2

    page = auth_client.get(recipe.get_absolute_url()).content.decode()
    assert "Proposer à la communauté" in page
    auth_client.post(reverse("assistant:propose", args=[recipe.slug]))
    recipe.refresh_from_db()
    assert recipe.review_requested

    auth_client.force_login(other_user)
    assert auth_client.get(recipe.get_absolute_url()).status_code == 404
    assert client.get(recipe.get_absolute_url()).status_code in (302, 404)


def test_fridge_rejects_recipe_without_known_ingredients(auth_client, fake_ai, stock):
    fake_ai.reply({**RECIPE, "ingredients": RECIPE["ingredients"][2:]})
    response = auth_client.post(
        reverse("assistant:fridge"),
        {"products": [stock.pk], "servings": 2, "mode": Mode.FAST},
    )
    assert "pas assez d&#x27;ingrédients" in response.content.decode()
    assert not Recipe.objects.filter(is_ai_generated=True).exists()


def test_fridge_preselects_expiring_products(auth_client, stock):
    stock.expires_on = timezone.localdate()
    stock.save()
    assert (
        f'value="{stock.pk}" checked'
        in auth_client.get(reverse("assistant:fridge")).content.decode()
    )


def _photo():
    buffer = io.BytesIO()
    Image.new("RGB", (2400, 1200), "white").save(buffer, "PNG")
    return SimpleUploadedFile("ticket.png", buffer.getvalue(), content_type="image/png")


def test_receipt_to_pantry(auth_client, fake_ai, ingredients, user):
    fake_ai.reply(
        {
            "store": "Biocoop",
            "date": "2026-10-20",
            "items": [
                {
                    "label": "Tomates grappe",
                    "ingredient": "Tomate",
                    "quantity": 1,
                    "unit": "kg",
                    "price": 3.2,
                },
                {"label": "Savon", "ingredient": "", "quantity": 1, "unit": "piece", "price": 0},
            ],
        }
    )
    response = auth_client.post(
        reverse("assistant:receipt"), {"photo": _photo(), "mode": Mode.FAST}
    )
    content = response.content.decode()
    assert "Biocoop" in content and "Tomates grappe" in content
    media_type, data = fake_ai.prompts[0].images[0]
    assert media_type == "image/jpeg" and max(Image.open(io.BytesIO(data)).size) == 1600

    formset = response.context["formset"]
    post = {"form-TOTAL_FORMS": "2", "form-INITIAL_FORMS": "2"}
    for index, form in enumerate(formset):
        for name, value in form.initial.items():
            if value not in (None, False):
                post[f"form-{index}-{name}"] = "on" if value is True else value
    post.pop("form-1-selected")
    auth_client.post(reverse("assistant:receipt_save"), post)
    item = PantryItem.objects.get(user=user)
    assert (item.name, item.ingredient, item.estimated_value) == (
        "Tomates grappe", ingredients["tomate"], Decimal("3.20"),
    )  # fmt: skip


def test_receipt_rejects_non_images(auth_client, fake_ai):
    upload = SimpleUploadedFile("x.pdf", b"%PDF", content_type="application/pdf")
    response = auth_client.post(reverse("assistant:receipt"), {"photo": upload, "mode": "fast"})
    assert "Choisissez une photo" in response.content.decode()
    assert fake_ai.prompts == []


def test_hub_lists_tools(client, db):
    content = client.get(reverse("assistant:hub")).content.decode()
    for name in ("plan_new", "fridge", "receipt"):
        assert reverse(f"assistant:{name}") in content


def test_fridge_keeps_unconvertible_amounts_as_notes(auth_client, fake_ai, stock):
    eggs = {"name": "Œuf", "quantity": 150, "unit": "g", "note": "battus"}
    fake_ai.reply({**RECIPE, "ingredients": [RECIPE["ingredients"][0], eggs]})
    auth_client.post(
        reverse("assistant:fridge"), {"products": [stock.pk], "servings": 2, "mode": Mode.FAST}
    )
    item = Recipe.objects.get(slug="omelette-du-frigo").items.get(ingredient__slug="oeuf")
    assert (item.quantity, item.unit, item.note) == (None, "piece", "150 g battus")


def test_plan_accepts_integer_budget(fake_ai, menu, user):
    plan = MealPlan.objects.create(user=user, days=3, servings=2, budget=20)
    fake_ai.reply({"meals": [], "summary": "", "tips": []})
    assert planner.generate(plan, Caller(user, "")).status == MealPlan.Status.READY
