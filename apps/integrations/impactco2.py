from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from .http import JsonClient, ServiceError

DAY = 24 * 3600


@dataclass(frozen=True)
class SeasonalProduce:
    name: str
    slug: str
    category: str
    months: tuple[int, ...]
    co2_per_kg: Decimal


def _client() -> JsonClient:
    conf = settings.INTEGRATIONS
    headers = (
        {"Authorization": f"Bearer {conf['IMPACT_CO2_API_KEY']}"}
        if conf["IMPACT_CO2_API_KEY"]
        else {}
    )
    return JsonClient(conf["IMPACT_CO2_URL"], headers=headers, cache_ttl=7 * DAY)


def _decimal(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.001"))


def seasonal_produce(month: int | None = None) -> list[SeasonalProduce]:
    params = {"month": month} if month else None
    data = _client().get("/fruitsetlegumes", params) or {}
    return [
        SeasonalProduce(
            name=item["name"],
            slug=item["slug"],
            category=item.get("category", ""),
            months=tuple(item.get("months") or ()),
            co2_per_kg=_decimal(item.get("ecv")),
        )
        for item in data.get("data", [])
    ]


def food_footprints() -> dict[str, Decimal]:
    """kg CO2e per kg of food, keyed by Impact CO2 slug."""
    client = _client()
    footprints: dict[str, Decimal] = {}
    produce = client.get("/fruitsetlegumes") or {}
    for item in produce.get("data", []):
        footprints[item["slug"]] = _decimal(item.get("ecv"))
    groups = client.get("/alimentation", {"category": "group"}) or {}
    for group in groups.get("data", []):
        for item in group.get("items", []):
            footprints[item["slug"]] = _decimal(item.get("ecv"))
    return footprints


def safe_food_footprints() -> dict[str, Decimal]:
    try:
        return food_footprints()
    except ServiceError:
        return {}


def seasonal_slugs(month: int) -> set[str]:
    try:
        return {item.slug for item in seasonal_produce(month)}
    except ServiceError:
        return set()
