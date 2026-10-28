import io
from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.assistant import cook
from apps.assistant.models import Feature
from apps.billing.models import Plan, PlanQuota
from apps.recipes.models import Ingredient, Recipe
from apps.shopping.models import ShoppingList

pytestmark = pytest.mark.django_db

DISH = {
    "title": "Riz sauce tomate",
    "summary": "Simple et réconfortant.",
    "course": "main",
    "cuisine": "africa",
    "difficulty": 1,
    "prep_minutes": 10,
    "cook_minutes": 25,
    "ingredients": [
        {"name": "Tomate", "quantity": 400, "unit": "g", "note": ""},
        {"name": "Riz", "quantity": 200, "unit": "g", "note": ""},
        {"name": "Gombo", "quantity": 150, "unit": "g", "note": "en rondelles"},
        {"name": "Sel", "quantity": 1, "unit": "pinch", "note": ""},
    ],
    "new_ingredients": [
        {
            "name": "Gombo", "aisle": "produce", "price_unit": "kg", "unit_weight_g": 0,
            "off_category": "en:okras",
        },
        {
            "name": "Licorne", "aisle": "other", "price_unit": "kg", "unit_weight_g": 0,
            "off_category": "pas une catégorie",
        },
    ],
    "steps": ["Cuire le riz.", "Préparer la sauce."],
}  # fmt: skip


@pytest.fixture
def rice(ingredients):
    return Ingredient.objects.create(name="Riz", aisle="grocery", price_unit="kg")


def test_split_names_and_dish():
    assert cook.split_names("des pommes, du riz et de l'ail") == ["pommes", "riz", "ail"]
    assert cook.split_names("lait; la tomate") == ["lait", "tomate"]
    assert cook.split_dish("Riz sauce tomate pour 2 personnes") == ("Riz sauce tomate", 2)
    assert cook.split_dish("mafé") == ("mafé", None)


def test_parse_have_resolves_known_ingredients(ingredients):
    found, unknown = cook.parse_have("tomates, oeufs, licorne")
    assert [i.slug for i in found] == ["tomate", "oeuf"] and unknown == ["licorne"]


def test_find_dish_needs_every_word_in_the_title(recipe):
    match, close = cook.find_dish("omelette aux tomates", None)
    assert match == recipe and close == []
    match, close = cook.find_dish("omelette au jambon", None)
    assert match is None and close == [recipe]


def test_plan_prices_only_what_is_missing(recipe, ingredients, prices):
    plan = cook.plan_for(recipe, 2, {ingredients["oeuf"].pk}, None)
    assert [n.item.ingredient.slug for n in plan.have] == ["oeuf"]
    assert [n.item.ingredient.slug for n in plan.missing] == ["tomate"]
    assert [n.item.ingredient.slug for n in plan.staples] == ["sel"]
    assert plan.best.brand == "Discount" and plan.missing_total == Decimal("0.50")
    assert plan.saving == Decimal("1.40") and plan.coverage == 50


def test_suggestions_favour_fewer_purchases(recipe, menu_like, ingredients):
    plans = cook.suggest({ingredients["oeuf"].pk}, None, 2, None)
    assert plans[0].recipe.title == "Flan" and not plans[0].missing


@pytest.fixture
def menu_like(ingredients):
    flan = Recipe.objects.create(title="Flan", servings=2)
    flan.items.create(ingredient=ingredients["oeuf"], quantity=Decimal(3), unit="piece")
    return flan


def test_cook_page_shows_catalogue_dish(client, recipe, prices):
    url = reverse("assistant:cook")
    page = client.get(url, {"envie": "omelette tomate pour 4", "j": "oeufs"}).content.decode()
    assert "Omelette tomate" in page and "4 personnes" in page
    assert "Discount" in page and "Déjà chez vous" in page


def test_cook_page_suggests_from_ingredients(client, recipe):
    page = client.get(reverse("assistant:cook"), {"j": "oeufs, tomates"}).content.decode()
    assert "Avec ce que vous avez" in page and "Omelette tomate" in page


def test_unknown_dish_asks_visitors_to_log_in(client, recipe):
    page = client.get(reverse("assistant:cook"), {"envie": "mafé"}).content.decode()
    assert "n'est pas encore au catalogue" in page and "Créer un compte gratuit" in page
    assert 'hx-trigger="load"' not in page


def test_unknown_dish_is_generated_for_members(auth_client, fake_ai, ai_config, rice, user):
    page = auth_client.get(reverse("assistant:cook"), {"envie": "riz sauce tomate"})
    assert 'hx-trigger="load"' in page.content.decode()
    fake_ai.reply(DISH)
    response = auth_client.post(
        reverse("assistant:cook_create"),
        {"envie": "riz sauce tomate pour 2", "j": "riz", "mode": "fast"},
        HTTP_HX_REQUEST="true",
    )
    recipe = Recipe.objects.get(slug="riz-sauce-tomate")
    assert recipe.author == user and recipe.review_requested and recipe.cuisine == "africa"
    assert recipe.servings == 2 and not recipe.is_published
    assert "recette=riz-sauce-tomate" in response["HX-Replace-Url"]
    gombo = Ingredient.objects.get(name="Gombo")
    assert gombo.is_draft and gombo.off_category == "en:okras"
    assert not Ingredient.objects.filter(name="Licorne").exists()
    assert [i.ingredient.name for i in recipe.items.all()] == ["Tomate", "Riz", "Gombo", "Sel"]
    page = response.content.decode()
    assert "Déjà chez vous" in page and "Riz" in page
    prompt = fake_ai.prompts[0].text
    assert "<<<riz sauce tomate>>>" in prompt and "disponibles : Riz" in prompt


def test_invent_needs_two_ingredients(auth_client, fake_ai):
    response = auth_client.post(reverse("assistant:cook_create"), {"j": "riz"})
    assert "au moins deux ingrédients" in response.content.decode() and not fake_ai.prompts


def test_cook_create_reports_quota(auth_client, fake_ai, ai_config, user):
    plan = Plan.objects.create(slug="gratuit", name="Gratuit", is_default=True)
    PlanQuota.objects.create(plan=plan, feature=Feature.RECIPE, daily=0)
    page = auth_client.post(reverse("assistant:cook_create"), {"envie": "mafé"}).content
    assert "Voir les formules" in page.decode() and not fake_ai.prompts


def _photo():
    buffer = io.BytesIO()
    Image.new("RGB", (40, 30), "orange").save(buffer, "PNG")
    return SimpleUploadedFile("frigo.png", buffer.getvalue(), content_type="image/png")


def test_photo_adds_recognised_foods(auth_client, fake_ai):
    fake_ai.reply(
        {"items": [{"name": "Tomates", "ingredient": "Tomate"}, {"name": "riz", "ingredient": ""}]}
    )
    response = auth_client.post(reverse("assistant:cook_photo"), {"j": "riz", "photo": _photo()})
    page = response.content.decode()
    assert 'value="riz, Tomate"' in page and "1 aliment" not in page
    assert fake_ai.prompts[0].images[0][0] == "image/jpeg"


def test_photo_rejects_other_files(auth_client, fake_ai):
    upload = SimpleUploadedFile("note.txt", b"hello", content_type="text/plain")
    page = auth_client.post(reverse("assistant:cook_photo"), {"photo": upload}).content.decode()
    assert "Choisissez une photo" in page and not fake_ai.prompts


def test_missing_items_go_to_the_shopping_list(auth_client, recipe, ingredients, user):
    auth_client.post(
        reverse("shopping:add_recipe"),
        {"recipe": recipe.pk, "servings": 2, "have": [ingredients["oeuf"].pk]},
    )
    shopping_list = ShoppingList.objects.get(user=user)
    assert [item.label for item in shopping_list.items.all()] == ["Tomate"]


def test_admin_generates_catalogue_recipes(admin_client, fake_ai, rice):
    url = reverse("admin:recipes_recipe_generate_with_ai")
    fake_ai.reply({"dishes": [{"name": "Riz sauce tomate", "why": "Pas cher."}]})
    page = admin_client.post(
        url, {"action": "suggest", "s-cuisine": "africa", "s-course": "", "s-count": 5}
    ).content.decode()
    assert "Riz sauce tomate" in page and "Pas cher." in page
    page = admin_client.post(
        url,
        {"action": "generate", "g-dishes": "Riz sauce tomate\nRiz sauce tomate", "g-cuisine": "",
         "g-servings": 4, "g-mode": "fast"},
    ).content.decode()  # fmt: skip
    assert page.count('name="name" value="Riz sauce tomate"') == 1
    fake_ai.reply(DISH)
    row = admin_client.post(
        reverse("admin:recipes_recipe_generate_one"),
        {"name": "Riz sauce tomate", "servings": 4, "cuisine": "africa", "mode": "fast"},
    ).content.decode()
    recipe = Recipe.objects.get(slug="riz-sauce-tomate")
    assert recipe.title in row and "1 à vérifier" in row and recipe.review_requested
