from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from decimal import Decimal
from statistics import median

from django.conf import settings
from django.utils import timezone

from apps.recipes.models import Ingredient
from apps.recipes.units import convert_unit_price, to_base

from .models import PriceObservation, Store, distance_km

CENT = Decimal("0.01")
MIN_BRAND_COVERAGE = 0.4


@dataclass
class Line:
    ingredient: Ingredient
    quantity: Decimal | None
    unit: str


@dataclass
class PricedLine:
    ingredient: Ingredient
    base_quantity: Decimal | None
    unit_price: Decimal | None
    observations: int = 0

    @property
    def cost(self) -> Decimal | None:
        if self.base_quantity is None or self.unit_price is None:
            return None
        return (self.base_quantity * self.unit_price).quantize(CENT)


@dataclass
class NearbyStore:
    store: Store
    distance_km: float | None


@dataclass
class Offer:
    brand: str
    logo_url: str
    total: Decimal
    priced: int
    fallback: int
    stores: list[NearbyStore] = field(default_factory=list)

    @property
    def coverage(self) -> int:
        count = self.priced + self.fallback
        return round(100 * self.priced / count) if count else 0


@dataclass
class BasketEstimate:
    lines: list[PricedLine]
    offers: list[Offer]

    @property
    def priceable(self) -> list[PricedLine]:
        return [line for line in self.lines if line.base_quantity is not None]

    @property
    def total(self) -> Decimal:
        return sum((line.cost for line in self.lines if line.cost is not None), Decimal(0))

    @property
    def coverage(self) -> int:
        priceable = self.priceable
        priced = [line for line in priceable if line.cost is not None]
        return round(100 * len(priced) / len(priceable)) if priceable else 0

    @property
    def cheapest(self) -> Offer | None:
        return self.offers[0] if self.offers else None

    @property
    def max_saving(self) -> Decimal:
        if len(self.offers) < 2:
            return Decimal(0)
        return self.offers[-1].total - self.offers[0].total


def _observations(ingredient_ids, since):
    return (
        PriceObservation.objects.filter(
            ingredient_id__in=ingredient_ids, observed_on__gte=since, is_discounted=False
        )
        .select_related("store")
        .only(
            "ingredient_id",
            "unit_price",
            "base_unit",
            "store__id",
            "store__brand",
            "store__name",
            "store__city",
            "store__latitude",
            "store__longitude",
            "store__logo_url",
            "store__osm_type",
            "store__osm_id",
        )
    )


def _distance(store: Store, near) -> float | None:
    if not near or store.latitude is None or store.longitude is None:
        return None
    return distance_km(near[0], near[1], store.latitude, store.longitude)


def estimate(
    lines: list[Line], *, near: tuple[float, float, float] | None = None
) -> BasketEstimate:
    """Estimate a basket with median observed prices, overall and per store brand.

    `near` is (latitude, longitude, radius_km): brand offers then only use nearby stores.
    """
    ingredients = {line.ingredient.pk: line.ingredient for line in lines}
    since = timezone.localdate() - timedelta(days=settings.PRICING["HISTORY_DAYS"])

    market: dict[int, list[Decimal]] = defaultdict(list)
    by_brand: dict[str, dict[int, list[Decimal]]] = defaultdict(lambda: defaultdict(list))
    brand_stores: dict[str, dict[int, NearbyStore]] = defaultdict(dict)
    logos: dict[str, str] = {}

    for obs in _observations(ingredients.keys(), since):
        ingredient = ingredients[obs.ingredient_id]
        price = convert_unit_price(
            obs.unit_price, obs.base_unit, ingredient.price_unit, ingredient.unit_weight_g
        )
        if price is None:
            continue
        market[obs.ingredient_id].append(price)
        store = obs.store
        if not store or not store.brand:
            continue
        distance = _distance(store, near)
        if near and (distance is None or distance > near[2]):
            continue
        by_brand[store.brand][obs.ingredient_id].append(price)
        brand_stores[store.brand].setdefault(store.pk, NearbyStore(store, distance))
        logos.setdefault(store.brand, store.logo_url)

    priced_lines = []
    for line in lines:
        ingredient = line.ingredient
        prices = market.get(ingredient.pk, [])
        priced_lines.append(
            PricedLine(
                ingredient=ingredient,
                base_quantity=to_base(
                    line.quantity, line.unit, ingredient.price_unit, ingredient.unit_weight_g
                ),
                unit_price=median(prices) if prices else None,
                observations=len(prices),
            )
        )

    priceable = [line for line in priced_lines if line.cost is not None]
    offers = []
    for brand, brand_prices in by_brand.items():
        total, priced, fallback = Decimal(0), 0, 0
        for line in priceable:
            prices = brand_prices.get(line.ingredient.pk)
            if prices:
                total += line.base_quantity * median(prices)
                priced += 1
            else:
                total += line.cost
                fallback += 1
        if priceable and priced / len(priceable) >= MIN_BRAND_COVERAGE:
            stores = sorted(
                brand_stores[brand].values(),
                key=lambda s: s.distance_km if s.distance_km is not None else 0,
            )
            offers.append(
                Offer(
                    brand, logos.get(brand, ""), total.quantize(CENT), priced, fallback, stores[:3]
                )
            )

    offers.sort(key=lambda offer: (offer.total, -offer.priced))
    return BasketEstimate(lines=priced_lines, offers=offers)
