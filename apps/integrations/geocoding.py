from dataclasses import dataclass

from django.conf import settings

from .http import JsonClient


@dataclass(frozen=True)
class Place:
    label: str
    city: str
    postal_code: str
    latitude: float
    longitude: float


def geocode_city(query: str) -> Place | None:
    """Resolve a French postal code or city name with the IGN Géoplateforme."""
    query = (query or "").strip()
    if len(query) < 3:
        return None
    client = JsonClient(settings.INTEGRATIONS["GEOCODING_URL"], cache_ttl=30 * 24 * 3600)
    data = client.get("/search", {"q": query, "type": "municipality", "limit": 1}) or {}
    features = data.get("features") or []
    if not features:
        return None
    props = features[0]["properties"]
    lon, lat = features[0]["geometry"]["coordinates"]
    return Place(
        label=props.get("label", ""),
        city=props.get("city") or props.get("name", ""),
        postal_code=props.get("postcode", ""),
        latitude=lat,
        longitude=lon,
    )
