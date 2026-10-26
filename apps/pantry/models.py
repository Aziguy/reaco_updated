from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.core.models import TimeStampedModel
from apps.recipes.models import Ingredient
from apps.recipes.units import Unit

SOON_DAYS = 3


class PantryQuerySet(models.QuerySet):
    def in_stock(self):
        return self.filter(status=PantryItem.Status.IN_STOCK)

    def expiring(self, days: int = SOON_DAYS):
        limit = timezone.localdate() + timedelta(days=days)
        return self.in_stock().filter(expires_on__isnull=False, expires_on__lte=limit)


class PantryItem(TimeStampedModel):
    class Status(models.TextChoices):
        IN_STOCK = "in_stock", "En stock"
        CONSUMED = "consumed", "Consommé"
        WASTED = "wasted", "Jeté"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pantry_items"
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="pantry_items",
        verbose_name="ingrédient",
    )
    name = models.CharField("produit", max_length=200)
    brand = models.CharField("marque", max_length=120, blank=True)
    barcode = models.CharField("code-barres", max_length=14, blank=True)
    image_url = models.URLField(blank=True)
    nutriscore = models.CharField("Nutri-Score", max_length=1, blank=True)
    green_score = models.CharField("Green-Score", max_length=1, blank=True)
    quantity = models.DecimalField(
        "quantité", max_digits=8, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField("unité", max_length=10, choices=Unit, default=Unit.PIECE)
    expires_on = models.DateField("à consommer avant le", null=True, blank=True)
    estimated_value = models.DecimalField(
        "valeur estimée (€)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    status = models.CharField(max_length=10, choices=Status, default=Status.IN_STOCK)
    closed_on = models.DateField("sorti le", null=True, blank=True)

    objects = PantryQuerySet.as_manager()

    class Meta:
        ordering = [models.F("expires_on").asc(nulls_last=True), "name", "pk"]
        verbose_name = "article du garde-manger"
        verbose_name_plural = "garde-manger"
        indexes = [models.Index(fields=["user", "status", "expires_on"])]

    def __str__(self):
        return self.name

    @property
    def days_left(self) -> int | None:
        if self.expires_on is None:
            return None
        return (self.expires_on - timezone.localdate()).days

    @property
    def days_overdue(self) -> int:
        days = self.days_left
        return -days if days is not None and days < 0 else 0

    @property
    def urgency(self) -> str:
        days = self.days_left
        if days is None:
            return "none"
        if days < 0:
            return "expired"
        if days <= SOON_DAYS:
            return "soon"
        return "ok"

    def close(self, status: str):
        self.status = status
        self.closed_on = timezone.localdate()
        self.save(update_fields=["status", "closed_on", "updated_at"])
