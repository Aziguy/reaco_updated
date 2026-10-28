from datetime import date, timedelta
from decimal import Decimal

import pytest
import respx
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret
from django.core.cache import cache

from apps.assistant import services
from apps.assistant.models import AIModel, Feature, Mode, Provider, Route
from apps.assistant.providers import AIError, Completion
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


def with_mfa(user):
    TOTP.activate(user, generate_totp_secret())
    return user


@pytest.fixture
def admin_user(django_user_model):
    """Staff accounts need two-factor authentication to open the admin."""
    admin = django_user_model.objects.create_superuser(email="admin@example.com", password="x")
    return with_mfa(admin)


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


class FakeClient:
    def __init__(self, replies, prompts):
        self.replies = replies
        self.prompts = prompts

    def complete(self, prompt):
        self.prompts.append(prompt)
        reply = self.replies.pop(0) if self.replies else {}
        if isinstance(reply, Exception):
            raise reply
        return Completion(reply, input_tokens=1000, output_tokens=200)


class FakeAI:
    """Queue replies (dicts or AIError) answered by any model, and record prompts."""

    def __init__(self):
        self.replies: list = []
        self.prompts: list = []
        self.models: list = []

    def reply(self, *replies):
        self.replies.extend(replies)

    def fail(self, message="boom"):
        self.replies.append(AIError(message))


@pytest.fixture
def ai_config(db, monkeypatch):
    monkeypatch.setenv("TEST_AI_KEY", "test")
    provider = Provider.objects.create(
        name="Test", kind=Provider.Kind.ANTHROPIC, api_key_env="TEST_AI_KEY"
    )
    main = AIModel.objects.create(
        provider=provider, model_id="main", label="Main", supports_vision=True,
        supports_effort=True, input_price=1, output_price=5,
    )  # fmt: skip
    backup = AIModel.objects.create(provider=provider, model_id="backup", label="Backup")
    for feature in Feature.values:
        for mode in Mode.values:
            Route.objects.create(
                feature=feature, mode=mode, model=main, fallback=backup,
                daily_quota=5, anonymous_quota=2 if feature == Feature.SEARCH else 0,
            )  # fmt: skip
    return {"main": main, "backup": backup}


@pytest.fixture
def fake_ai(ai_config, monkeypatch):
    fake = FakeAI()

    def client_for(model):
        fake.models.append(model.model_id)
        return FakeClient(fake.replies, fake.prompts)

    monkeypatch.setattr(services, "client_for", client_for)
    return fake
