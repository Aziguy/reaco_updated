from decimal import Decimal

import httpx
import pytest

from apps.integrations import geocoding, impactco2, openfoodfacts, openprices
from apps.integrations.http import JsonClient, ServiceError

PRICES_URL = "https://prices.openfoodfacts.org/api/v1/prices"


def price_item(**overrides):
    item = {
        "id": 10,
        "price": 3.24,
        "currency": "EUR",
        "date": "2026-09-25",
        "price_per": None,
        "price_is_discounted": False,
        "product_code": "3228021170015",
        "product": {
            "product_name": "Beurre doux",
            "product_quantity": 250,
            "product_quantity_unit": "g",
        },
        "location": {
            "type": "OSM",
            "osm_id": 42,
            "osm_type": "NODE",
            "osm_name": "Carrefour Market",
            "osm_brand": "Carrefour Market",
            "osm_address_city": "Toulon",
            "osm_address_country_code": "FR",
            "osm_lat": 43.1,
            "osm_lon": 5.9,
        },
    }
    item.update(overrides)
    return item


class TestNormalize:
    def test_product_price_is_converted_per_kilogram(self):
        assert openprices.normalize(Decimal("3.24"), None, 250, "g") == (Decimal("12.960"), "kg")

    def test_volume_is_converted_per_liter(self):
        assert openprices.normalize(Decimal("1.50"), None, 1500, "ml") == (Decimal("1.000"), "l")

    def test_category_price_keeps_its_unit(self):
        assert openprices.normalize(Decimal("2.49"), "KILOGRAM", None, None) == (
            Decimal("2.49"),
            "kg",
        )
        assert openprices.normalize(Decimal("0.30"), "UNIT", None, None) == (
            Decimal("0.30"),
            "unit",
        )

    @pytest.mark.parametrize("qty, unit", [(None, "g"), (0, "g"), (6, None), (6, "pieces")])
    def test_unknown_quantity_is_rejected(self, qty, unit):
        assert openprices.normalize(Decimal(3), None, qty, unit) == (None, None)


class TestOpenPrices:
    def test_fetch_parses_records_and_stops_on_last_page(self, http):
        route = http.get(PRICES_URL).respond(json={"items": [price_item()], "pages": 1})
        records = openprices.fetch_prices(category_tag="en:butters")
        assert route.call_count == 1
        record = records[0]
        assert record.unit_price == Decimal("12.960")
        assert record.location.brand == "Carrefour Market"
        assert record.location.country_code == "FR"
        assert route.calls[0].request.url.params["category_tag"] == "en:butters"

    def test_invalid_items_are_skipped(self, http):
        http.get(PRICES_URL).respond(json={"items": [{"id": 1, "price": "x"}], "pages": 1})
        assert openprices.fetch_prices(product_code="123") == []


class TestJsonClient:
    def test_retries_then_caches_success(self, http):
        route = http.get("https://api.test/data").mock(
            side_effect=[httpx.Response(503), httpx.Response(200, json={"ok": True})]
        )
        client = JsonClient("https://api.test")
        assert client.get("/data") == {"ok": True}
        assert client.get("/data") == {"ok": True}
        assert route.call_count == 2

    def test_failure_is_remembered(self, http):
        route = http.get("https://api.test/down").respond(500)
        client = JsonClient("https://api.test")
        with pytest.raises(ServiceError):
            client.get("/down")
        calls = route.call_count
        with pytest.raises(ServiceError):
            client.get("/down")
        assert route.call_count == calls

    def test_not_found_returns_none(self, http):
        http.get("https://api.test/missing").respond(404)
        assert JsonClient("https://api.test").get("/missing") is None


class TestOpenFoodFacts:
    def test_get_product(self, http):
        http.get(url__regex=r".*/api/v2/product/3017620422003").respond(
            json={
                "status": 1,
                "product": {
                    "code": "3017620422003",
                    "product_name": "Nutella",
                    "brands": "Nutella, Ferrero",
                    "nutriscore_grade": "e",
                    "ecoscore_grade": "unknown",
                    "nova_group": 3,
                    "product_quantity": "400",
                    "product_quantity_unit": "g",
                    "categories_tags": ["en:spreads"],
                },
            }
        )
        product = openfoodfacts.get_product("3017620422003")
        assert product.brand == "Nutella"
        assert product.nutriscore == "e"
        assert product.green_score == ""
        assert product.quantity_value == 400

    def test_invalid_barcode_skips_request(self, http):
        assert openfoodfacts.get_product("abc") is None


def test_food_footprints_merge_both_endpoints(http):
    http.get("https://impactco2.fr/api/v1/fruitsetlegumes").respond(
        json={"data": [{"name": "Tomate", "slug": "tomate", "months": [7, 8], "ecv": 0.5}]}
    )
    http.get("https://impactco2.fr/api/v1/alimentation").respond(
        json={"data": [{"slug": "viandes", "items": [{"slug": "boeuf", "ecv": 28.0}]}]}
    )
    footprints = impactco2.food_footprints()
    assert footprints == {"tomate": Decimal("0.500"), "boeuf": Decimal("28.000")}


def test_safe_footprints_survive_outage():
    assert impactco2.safe_food_footprints() == {}


def test_geocode_city(http):
    http.get("https://data.geopf.fr/geocodage/search").respond(
        json={
            "features": [
                {
                    "geometry": {"coordinates": [5.93, 43.13]},
                    "properties": {"label": "Toulon", "city": "Toulon", "postcode": "83000"},
                }
            ]
        }
    )
    place = geocoding.geocode_city("83000")
    assert (place.city, place.latitude, place.longitude) == ("Toulon", 43.13, 5.93)
