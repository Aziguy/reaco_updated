from datetime import date
from decimal import Decimal

import pytest

from apps.integrations.openprices import Location, PriceRecord
from apps.pricing.estimator import Line, estimate, estimate_near
from apps.pricing.models import PriceObservation, Store
from apps.pricing.sync import normalize_brand, store_records

TOULON = (43.12, 5.93, 20)


def record(record_id, country="FR", unit_price=Decimal("3.000"), brand="E. Leclerc"):
    location = Location(
        osm_type="NODE", osm_id=record_id, name="Magasin", brand=brand, city="Toulon",
        postcode="83000", country_code=country, latitude=43.1, longitude=5.9, logo_url="",
    )  # fmt: skip
    return PriceRecord(
        id=record_id, price=Decimal(3), currency="EUR", observed_on=date.today(),
        is_discounted=False, unit_price=unit_price, base_unit="kg", product_code="",
        product_name="", category_tag="en:tomatoes", location=location,
    )  # fmt: skip


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("E. Leclerc  Drive", "E.Leclerc Drive"),
        ("Centre commercial E.Leclerc", "E.Leclerc"),
        ("ALDI", "Aldi"),
        ("monop'", "Monop'"),
        ("G20", "G20"),
    ],
)
def test_normalize_brand(raw, expected):
    assert normalize_brand(raw) == expected


@pytest.mark.django_db
class TestStoreRecords:
    def test_filters_country_and_invalid_prices(self, ingredients):
        records = [record(1), record(2, country="DE"), record(3, unit_price=None)]
        assert store_records(ingredients["tomate"], records) == 1
        assert Store.objects.get().brand == "E.Leclerc"

    def test_is_idempotent(self, ingredients):
        store_records(ingredients["tomate"], [record(1)])
        assert store_records(ingredients["tomate"], [record(1)]) == 0
        assert PriceObservation.objects.count() == 1


class TestEstimator:
    def lines(self, ingredients):
        return [
            Line(ingredients["tomate"], Decimal(500), "g"),
            Line(ingredients["oeuf"], Decimal(6), "piece"),
            Line(ingredients["lait"], Decimal(1), "l"),
        ]

    def test_median_and_coverage(self, ingredients, prices):
        basket = estimate(self.lines(ingredients))
        tomato, eggs, milk = basket.lines
        assert tomato.unit_price == Decimal(3)
        assert tomato.cost == Decimal("1.50")
        assert eggs.cost == Decimal("2.10")
        assert milk.cost is None
        assert basket.total == Decimal("3.60")
        assert basket.coverage == 67

    def test_offers_are_ranked(self, ingredients, prices):
        basket = estimate(self.lines(ingredients))
        assert [offer.brand for offer in basket.offers] == ["Discount", "Premium"]
        assert basket.cheapest.total == Decimal("2.50")
        assert basket.saving == Decimal("1.10")

    def test_near_keeps_only_local_stores(self, ingredients, prices):
        basket = estimate(self.lines(ingredients), near=TOULON)
        assert [offer.brand for offer in basket.offers] == ["Discount"]
        assert basket.offers[0].stores[0].distance_km < 1

    def test_discounted_prices_are_ignored(self, ingredients, prices):
        PriceObservation.objects.update(is_discounted=True)
        assert estimate(self.lines(ingredients)).total == 0


@pytest.mark.django_db
def test_loose_prices_win_over_processed_products(ingredients):
    tomato = ingredients["tomate"]
    for index in range(5):
        PriceObservation.objects.create(
            source_id=100 + index, ingredient=tomato, price=2, unit_price=2, base_unit="kg",
            observed_on=date.today(),
        )  # fmt: skip
    PriceObservation.objects.create(
        source_id=200, ingredient=tomato, product_code="3560070000000", price=3, unit_price=30,
        base_unit="kg", observed_on=date.today(),
    )  # fmt: skip
    [line] = estimate([Line(tomato, Decimal(1), "kg")]).lines
    assert (line.unit_price, line.observations) == (Decimal(2), 5)


def test_estimate_near_falls_back_to_all_stores(ingredients, prices):
    lines = [Line(ingredients["tomate"], Decimal(1), "kg")]
    basket, local = estimate_near(lines, near=(48.85, 2.35, 5))
    assert not local
    assert len(basket.offers) == 2


@pytest.mark.django_db
def test_implausible_prices_are_ignored(ingredients, stores):
    tomato = ingredients["tomate"]
    rows = [("2.00", stores["cheap"]), ("2.20", stores["cheap"]), ("2.10", stores["fancy"])]
    rows.append(("90.00", stores["fancy"]))
    for index, (price, store) in enumerate(rows):
        PriceObservation.objects.create(
            source_id=300 + index, ingredient=tomato, store=store, price=Decimal(price),
            unit_price=Decimal(price), base_unit="kg", observed_on=date.today(),
        )  # fmt: skip
    basket = estimate([Line(tomato, Decimal(1), "kg")])
    assert basket.lines[0].observations == 3
    assert {offer.brand: offer.total for offer in basket.offers}["Premium"] == Decimal("2.10")
