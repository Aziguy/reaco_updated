from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation

from django.conf import settings

from .http import JsonClient

PAGE_SIZE = 100
MASS_UNITS = {"g": Decimal("0.001"), "kg": Decimal(1), "mg": Decimal("0.000001")}
VOLUME_UNITS = {"ml": Decimal("0.001"), "cl": Decimal("0.01"), "l": Decimal(1)}
PRICE_PER_UNITS = {"KILOGRAM": "kg", "LITER": "l", "UNIT": "unit"}


@dataclass(frozen=True)
class Location:
    osm_type: str
    osm_id: int
    name: str
    brand: str
    city: str
    postcode: str
    country_code: str
    latitude: float | None
    longitude: float | None
    logo_url: str


@dataclass(frozen=True)
class PriceRecord:
    id: int
    price: Decimal
    currency: str
    observed_on: date
    is_discounted: bool
    unit_price: Decimal | None
    base_unit: str | None
    product_code: str
    product_name: str
    category_tag: str
    location: Location | None


def _client() -> JsonClient:
    return JsonClient(settings.INTEGRATIONS["OPEN_PRICES_URL"], cache_ttl=6 * 3600)


def normalize(price: Decimal, price_per: str | None, qty: float | None, unit: str | None):
    """Return (unit_price, base_unit) where base_unit is kg, l or unit."""
    if price_per in PRICE_PER_UNITS:
        return price, PRICE_PER_UNITS[price_per]
    if not qty or qty <= 0 or not unit:
        return None, None
    unit = unit.lower()
    for factors, base in ((MASS_UNITS, "kg"), (VOLUME_UNITS, "l")):
        if unit in factors:
            amount = Decimal(str(qty)) * factors[unit]
            return (price / amount).quantize(Decimal("0.001")), base
    return None, None


def parse_location(data: dict | None) -> Location | None:
    if not data or data.get("type") != "OSM" or not data.get("osm_id"):
        return None
    return Location(
        osm_type=data.get("osm_type") or "",
        osm_id=int(data["osm_id"]),
        name=data.get("osm_name") or "",
        brand=data.get("osm_brand") or "",
        city=data.get("osm_address_city") or "",
        postcode=data.get("osm_address_postcode") or "",
        country_code=(data.get("osm_address_country_code") or "").upper(),
        latitude=data.get("osm_lat"),
        longitude=data.get("osm_lon"),
        logo_url=data.get("osm_brand_logo_url") or "",
    )


def parse_price(data: dict) -> PriceRecord | None:
    try:
        price = Decimal(str(data["price"]))
        observed_on = date.fromisoformat(data["date"])
    except (KeyError, TypeError, ValueError, InvalidOperation):
        return None
    product = data.get("product") or {}
    unit_price, base_unit = normalize(
        price,
        data.get("price_per"),
        product.get("product_quantity"),
        product.get("product_quantity_unit"),
    )
    return PriceRecord(
        id=int(data["id"]),
        price=price,
        currency=data.get("currency") or "",
        observed_on=observed_on,
        is_discounted=bool(data.get("price_is_discounted")),
        unit_price=unit_price,
        base_unit=base_unit,
        product_code=data.get("product_code") or "",
        product_name=product.get("product_name") or "",
        category_tag=data.get("category_tag") or "",
        location=parse_location(data.get("location")),
    )


def fetch_prices(
    *,
    category_tag: str | None = None,
    product_category: str | None = None,
    product_code: str | None = None,
    since: date | None = None,
    near: tuple[float, float, float] | None = None,
    max_pages: int = 3,
    currency: str = "EUR",
) -> list[PriceRecord]:
    params = {"currency": currency, "order_by": "-date", "size": PAGE_SIZE}
    if category_tag:
        params["category_tag"] = category_tag
    if product_category:
        params["product__categories_tags__contains"] = product_category
    if product_code:
        params["product_code"] = product_code
    if since:
        params["date__gte"] = since.isoformat()
    if near:
        params["lat"], params["lon"], params["radius_km"] = near

    client = _client()
    records: list[PriceRecord] = []
    for page in range(1, max_pages + 1):
        data = client.get("/api/v1/prices", {**params, "page": page}) or {}
        records.extend(r for r in map(parse_price, data.get("items", [])) if r)
        if page >= (data.get("pages") or 1):
            break
    return records
