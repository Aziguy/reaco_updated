from django.conf import settings
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel
from apps.recipes.models import Ingredient, Recipe
from apps.recipes.units import Unit, format_quantity


class ShoppingList(TimeStampedModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="shopping_lists"
    )
    name = models.CharField("nom", max_length=120, default="Mes courses")
    is_archived = models.BooleanField("archivée", default=False)

    class Meta:
        ordering = ["is_archived", "-updated_at"]
        verbose_name = "liste de courses"
        verbose_name_plural = "listes de courses"

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("shopping:detail", args=[self.pk])


class ShoppingItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    label = models.CharField("article", max_length=200)
    quantity = models.DecimalField(
        "quantité", max_digits=8, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField("unité", max_length=10, choices=Unit, blank=True)
    recipes = models.ManyToManyField(Recipe, blank=True, related_name="+")
    is_checked = models.BooleanField("dans le panier", default=False)

    class Meta:
        ordering = ["is_checked", "label"]
        verbose_name = "article"

    def __str__(self):
        return self.label

    @property
    def display_quantity(self) -> str:
        if self.quantity is None:
            return ""
        return f"{format_quantity(self.quantity)} {self.get_unit_display()}".strip()

    @property
    def aisle(self) -> str:
        return self.ingredient.get_aisle_display() if self.ingredient else "Autre"
