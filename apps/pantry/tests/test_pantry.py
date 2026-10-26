from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.pantry.models import PantryItem
from apps.pantry.services import lookup_barcode, stats_for, suggest_recipes

TODAY = timezone.localdate()


def add(user, name="Tomates", ingredient=None, days=None, **extra):
    expires_on = TODAY + timedelta(days=days) if days is not None else None
    return PantryItem.objects.create(
        user=user, name=name, ingredient=ingredient, expires_on=expires_on, **extra
    )


@pytest.mark.django_db
class TestModel:
    @pytest.mark.parametrize(
        "days, urgency", [(-1, "expired"), (0, "soon"), (3, "soon"), (10, "ok"), (None, "none")]
    )
    def test_urgency(self, user, days, urgency):
        assert add(user, days=days).urgency == urgency

    def test_close_sets_date(self, user):
        item = add(user)
        item.close(PantryItem.Status.CONSUMED)
        assert item.closed_on == TODAY
        assert not PantryItem.objects.in_stock().exists()


@pytest.mark.django_db
def test_stats(user):
    add(user, days=1)
    add(user, estimated_value=Decimal("2.50")).close(PantryItem.Status.CONSUMED)
    add(user, estimated_value=Decimal("1.20")).close(PantryItem.Status.WASTED)
    stats = stats_for(user)
    assert (stats.in_stock, stats.expiring, stats.consumed, stats.wasted) == (1, 1, 1, 1)
    assert stats.saved_value == Decimal("2.50")
    assert stats.anti_waste_rate == 50


def test_suggestions_favour_expiring_items(user, recipe, ingredients):
    add(user, ingredient=ingredients["tomate"], days=1)
    [suggestion] = suggest_recipes(user)
    assert suggestion.recipe == recipe
    assert [i.ingredient for i in suggestion.urgent] == [ingredients["tomate"]]
    assert [i.ingredient for i in suggestion.missing] == [ingredients["oeuf"]]
    assert suggestion.match_rate == 50


def test_lookup_barcode_links_ingredient(http, ingredients):
    http.get(url__regex=r".*/api/v2/product/").respond(
        json={
            "status": 1,
            "product": {
                "code": "3560070000000",
                "product_name": "Tomates cerises",
                "product_quantity": 250,
                "product_quantity_unit": "g",
                "categories_tags": ["en:plant-based-foods", "en:tomatoes"],
                "nutriscore_grade": "a",
            },
        }
    )
    http.get("https://prices.openfoodfacts.org/api/v1/prices").respond(
        json={"items": [{"id": 1, "price": 2.2, "date": "2026-10-01"}], "pages": 1}
    )
    data = lookup_barcode("3560070000000")
    assert data["ingredient"] == ingredients["tomate"].pk
    assert (data["quantity"], data["unit"]) == (Decimal(250), "g")
    assert data["estimated_value"] == Decimal("2.20")


@pytest.mark.django_db
class TestViews:
    def test_list_requires_login(self, client):
        assert client.get(reverse("pantry:list")).status_code == 302

    def test_add_item(self, auth_client, user):
        response = auth_client.post(
            reverse("pantry:add"), {"name": "Yaourts", "quantity": "4", "unit": "piece"}
        )
        assert response.status_code == 302
        assert user.pantry_items.get().name == "Yaourts"

    def test_external_image_url_is_dropped(self, auth_client, user):
        auth_client.post(
            reverse("pantry:add"),
            {"name": "X", "unit": "piece", "image_url": "https://evil.example/x.png"},
        )
        assert user.pantry_items.get().image_url == ""

    def test_close_via_htmx(self, auth_client, user):
        item = add(user)
        url = reverse("pantry:close", args=[item.pk, "wasted"])
        response = auth_client.post(url, HTTP_HX_REQUEST="true")
        assert response["HX-Trigger"] == "pantry-changed"
        item.refresh_from_db()
        assert item.status == PantryItem.Status.WASTED

    def test_invalid_status(self, auth_client, user):
        item = add(user)
        response = auth_client.post(reverse("pantry:close", args=[item.pk, "in_stock"]))
        assert response.status_code == 400

    def test_cannot_touch_other_users_items(self, auth_client, other_user):
        item = add(other_user)
        assert auth_client.post(reverse("pantry:delete", args=[item.pk])).status_code == 404
        assert auth_client.get(reverse("pantry:edit", args=[item.pk])).status_code == 404

    def test_lookup_unknown_product(self, auth_client, http):
        http.get(url__regex=r".*/api/v2/product/").respond(404)
        response = auth_client.get(reverse("pantry:lookup"), {"code": "12345678"})
        assert "introuvable" in response.content.decode()

    def test_suggestions_page_is_public(self, client):
        assert client.get(reverse("pantry:suggestions")).status_code == 200


@pytest.mark.django_db
def test_expiry_reminders(user, other_user):
    add(user, name="Lait", days=1)
    add(other_user, name="Crème", days=1)
    other_user.expiry_reminders = False
    other_user.save()
    call_command("send_expiry_reminders", stdout=StringIO())
    assert len(mail.outbox) == 1
    assert "Lait" in mail.outbox[0].body
