import re
from dataclasses import dataclass, field

from django.conf import settings

from .http import JsonClient

BARCODE_RE = re.compile(r"^\d{8,14}$")
PRODUCT_FIELDS = (
    "code,product_name,product_name_fr,brands,quantity,product_quantity,product_quantity_unit,"
    "image_front_small_url,nutriscore_grade,ecoscore_grade,nova_group,categories_tags"
)
VALID_GRADES = {"a", "b", "c", "d", "e"}


@dataclass(frozen=True)
class Product:
    code: str
    name: str
    brand: str = ""
    quantity: str = ""
    quantity_value: float | None = None
    quantity_unit: str = ""
    image_url: str = ""
    nutriscore: str = ""
    green_score: str = ""
    nova: int | None = None
    categories: tuple[str, ...] = field(default_factory=tuple)

    @property
    def url(self) -> str:
        return f"https://world.openfoodfacts.org/product/{self.code}"


def _grade(value) -> str:
    value = (value or "").lower()
    return value if value in VALID_GRADES else ""


def _client() -> JsonClient:
    return JsonClient(settings.INTEGRATIONS["OPEN_FOOD_FACTS_URL"], cache_ttl=24 * 3600)


def is_barcode(value: str) -> bool:
    return bool(BARCODE_RE.match(value or ""))


def parse_product(data: dict) -> Product:
    brands = (data.get("brands") or "").split(",")
    try:
        quantity_value = float(data.get("product_quantity") or 0) or None
    except (TypeError, ValueError):
        quantity_value = None
    return Product(
        code=str(data.get("code", "")),
        name=data.get("product_name_fr") or data.get("product_name") or "",
        brand=brands[0].strip(),
        quantity=data.get("quantity") or "",
        quantity_value=quantity_value,
        quantity_unit=(data.get("product_quantity_unit") or "").lower(),
        image_url=data.get("image_front_small_url") or "",
        nutriscore=_grade(data.get("nutriscore_grade")),
        green_score=_grade(data.get("ecoscore_grade")),
        nova=data.get("nova_group") if isinstance(data.get("nova_group"), int) else None,
        categories=tuple(data.get("categories_tags") or ()),
    )


def get_product(code: str) -> Product | None:
    if not is_barcode(code):
        return None
    data = _client().get(f"/api/v2/product/{code}", {"fields": PRODUCT_FIELDS})
    if not data or data.get("status") != 1 or not data.get("product"):
        return None
    return parse_product(data["product"])
