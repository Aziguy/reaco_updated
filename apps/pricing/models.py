import math

from django.db import models

from apps.recipes.models import Ingredient
from apps.recipes.units import BaseUnit

EARTH_RADIUS_KM = 6371.0


def distance_km(lat1, lon1, lat2, lon2) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi, d_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


class StoreQuerySet(models.QuerySet):
    def near(self, latitude: float, longitude: float, radius_km: float):
        lat_delta = radius_km / 111.0
        lon_delta = radius_km / (111.0 * max(math.cos(math.radians(latitude)), 0.01))
        return self.filter(
            latitude__range=(latitude - lat_delta, latitude + lat_delta),
            longitude__range=(longitude - lon_delta, longitude + lon_delta),
        )


class Store(models.Model):
    osm_type = models.CharField(max_length=10)
    osm_id = models.BigIntegerField()
    name = models.CharField("nom", max_length=200)
    brand = models.CharField("enseigne", max_length=120, blank=True, db_index=True)
    city = models.CharField("ville", max_length=120, blank=True)
    postcode = models.CharField("code postal", max_length=10, blank=True)
    country_code = models.CharField("pays", max_length=2, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    logo_url = models.URLField(blank=True)

    objects = StoreQuerySet.as_manager()

    class Meta:
        ordering = ["brand", "name"]
        verbose_name = "magasin"
        constraints = [
            models.UniqueConstraint(fields=["osm_type", "osm_id"], name="unique_osm_store")
        ]

    def __str__(self):
        return self.name

    @property
    def osm_url(self) -> str:
        return f"https://www.openstreetmap.org/{self.osm_type.lower()}/{self.osm_id}"


class PriceObservation(models.Model):
    source_id = models.PositiveIntegerField("identifiant Open Prices", unique=True)
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE, related_name="prices", null=True, blank=True
    )
    store = models.ForeignKey(
        Store, on_delete=models.SET_NULL, related_name="prices", null=True, blank=True
    )
    product_code = models.CharField(max_length=20, blank=True, db_index=True)
    product_name = models.CharField(max_length=200, blank=True)
    price = models.DecimalField("prix", max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="EUR")
    unit_price = models.DecimalField("prix unitaire", max_digits=10, decimal_places=3)
    base_unit = models.CharField(max_length=5, choices=BaseUnit)
    is_discounted = models.BooleanField("promotion", default=False)
    observed_on = models.DateField("relevé le", db_index=True)

    class Meta:
        ordering = ["-observed_on"]
        verbose_name = "relevé de prix"
        indexes = [models.Index(fields=["ingredient", "observed_on"])]

    def __str__(self):
        return f"{self.product_name or self.ingredient} {self.price} {self.currency}"

    @property
    def source_url(self) -> str:
        return f"https://prices.openfoodfacts.org/prices/{self.source_id}"
