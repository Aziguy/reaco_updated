import logging
import re
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.integrations import openprices
from apps.recipes.models import Ingredient

from .estimator import MIN_RAW_OBSERVATIONS
from .models import PriceObservation, Store

logger = logging.getLogger(__name__)


BRAND_PREFIX = re.compile(r"^(centre commercial|hypermarch[ée]|supermarch[ée])\s+", re.IGNORECASE)


def normalize_brand(brand: str) -> str:
    """Merge variants such as "E. Leclerc", "Centre commercial E.Leclerc" or "ALDI" and "Aldi"."""
    brand = BRAND_PREFIX.sub("", re.sub(r"\.\s+", ".", " ".join(brand.split())))
    if brand.isupper() and len(brand) > 3:
        return brand.title()
    return brand[:1].upper() + brand[1:]


def _store_for(location: openprices.Location) -> Store:
    store, _ = Store.objects.update_or_create(
        osm_type=location.osm_type,
        osm_id=location.osm_id,
        defaults={
            "name": location.name[:200],
            "brand": normalize_brand(location.brand)[:120],
            "city": location.city[:120],
            "postcode": location.postcode[:10],
            "country_code": location.country_code[:2],
            "latitude": location.latitude,
            "longitude": location.longitude,
            "logo_url": location.logo_url,
        },
    )
    return store


def _accept(record: openprices.PriceRecord, countries: set[str]) -> bool:
    if record.unit_price is None or record.unit_price <= 0:
        return False
    location = record.location
    return not (location and countries and location.country_code not in countries)


@transaction.atomic
def store_records(ingredient: Ingredient | None, records) -> int:
    countries = set(settings.PRICING["COUNTRIES"])
    stores: dict[tuple[str, int], Store] = {}
    created = 0
    for record in records:
        if not _accept(record, countries):
            continue
        store = None
        if record.location:
            key = (record.location.osm_type, record.location.osm_id)
            store = stores.get(key)
            if store is None:
                store = stores[key] = _store_for(record.location)
        _, was_created = PriceObservation.objects.update_or_create(
            source_id=record.id,
            defaults={
                "ingredient": ingredient,
                "store": store,
                "product_code": record.product_code[:20],
                "product_name": record.product_name[:200],
                "price": record.price,
                "currency": record.currency,
                "unit_price": record.unit_price,
                "base_unit": record.base_unit,
                "is_discounted": record.is_discounted,
                "observed_on": record.observed_on,
            },
        )
        created += was_created
    return created


def sync_ingredient(ingredient: Ingredient, *, days: int | None = None, max_pages: int = 3) -> int:
    """Fetch recent Open Prices observations for an ingredient category."""
    if not ingredient.off_category:
        return 0
    days = days or settings.PRICING["HISTORY_DAYS"]
    since = timezone.localdate() - timedelta(days=days)
    currency = settings.PRICING["CURRENCY"]
    records = openprices.fetch_prices(
        category_tag=ingredient.off_category, since=since, max_pages=max_pages, currency=currency
    )
    created = store_records(ingredient, records)
    loose = sum(1 for r in records if r.unit_price is not None)
    if loose < MIN_RAW_OBSERVATIONS:
        products = openprices.fetch_prices(
            product_category=ingredient.off_category,
            since=since,
            max_pages=max_pages,
            currency=currency,
        )
        created += store_records(ingredient, products)
        records += products
    logger.info("Synced %s: %s records, %s new", ingredient.slug, len(records), created)
    return created
