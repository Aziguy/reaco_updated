import os
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import formats, timezone

from apps.core.models import TimeStampedModel
from apps.recipes.models import Diet, Recipe

MILLION = Decimal(1_000_000)


class Feature(models.TextChoices):
    SEARCH = "search", "Recherche"
    PLANNER = "planner", "Menu de la semaine"
    RECIPE = "recipe", "Création de recette"
    RECEIPT = "receipt", "Ticket de caisse"
    PHOTO = "photo", "Photo des ingrédients"
    CATALOG = "catalog", "Catalogue (admin)"


class Mode(models.TextChoices):
    FAST = "fast", "Rapide"
    DEEP = "deep", "Approfondi"


class Effort(models.TextChoices):
    DEFAULT = "", "Par défaut du modèle"
    LOW = "low", "Faible"
    MEDIUM = "medium", "Moyen"
    HIGH = "high", "Élevé"


class Provider(models.Model):
    class Kind(models.TextChoices):
        ANTHROPIC = "anthropic", "Anthropic"
        OPENAI = "openai", "Compatible OpenAI (GitHub Models, Mistral, Ollama…)"

    name = models.CharField("nom", max_length=60, unique=True)
    kind = models.CharField("type", max_length=20, choices=Kind)
    base_url = models.URLField(
        "URL de l'API",
        blank=True,
        help_text="Vide pour Anthropic. Par ex. https://models.github.ai/inference ou "
        "http://localhost:11434/v1 pour Ollama.",
    )
    api_key_env = models.CharField(
        "variable de la clé",
        max_length=60,
        blank=True,
        help_text="Nom de la variable d'environnement qui contient la clé, jamais la clé.",
    )
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "fournisseur"

    def __str__(self):
        return self.name

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "") if self.api_key_env else ""

    @property
    def is_configured(self) -> bool:
        if self.kind == self.Kind.ANTHROPIC:
            return bool(self.api_key)
        return bool(self.base_url) and (not self.api_key_env or bool(self.api_key))


class AIModel(models.Model):
    provider = models.ForeignKey(
        Provider, on_delete=models.CASCADE, related_name="models", verbose_name="fournisseur"
    )
    model_id = models.CharField("identifiant", max_length=120)
    label = models.CharField("libellé", max_length=80)
    supports_vision = models.BooleanField("lit les images", default=False)
    supports_effort = models.BooleanField("niveau de réflexion réglable", default=False)
    input_price = models.DecimalField(
        "prix entrée ($ / million de jetons)", max_digits=8, decimal_places=3, default=0
    )
    output_price = models.DecimalField(
        "prix sortie ($ / million de jetons)", max_digits=8, decimal_places=3, default=0
    )
    is_active = models.BooleanField("actif", default=True)

    class Meta:
        ordering = ["provider__name", "label"]
        verbose_name = "modèle"
        constraints = [
            models.UniqueConstraint(fields=["provider", "model_id"], name="unique_provider_model")
        ]

    def __str__(self):
        return f"{self.label} ({self.provider})"

    @property
    def is_available(self) -> bool:
        return self.is_active and self.provider.is_active and self.provider.is_configured

    def cost(self, input_tokens: int, output_tokens: int) -> Decimal:
        return (input_tokens * self.input_price + output_tokens * self.output_price) / MILLION


class Route(models.Model):
    feature = models.CharField("fonctionnalité", max_length=20, choices=Feature)
    mode = models.CharField(max_length=10, choices=Mode, default=Mode.FAST)
    model = models.ForeignKey(
        AIModel, on_delete=models.PROTECT, related_name="+", verbose_name="modèle"
    )
    fallback = models.ForeignKey(
        AIModel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="modèle de secours",
    )
    effort = models.CharField(
        "niveau de réflexion", max_length=10, choices=Effort, blank=True, default=Effort.LOW
    )
    max_tokens = models.PositiveIntegerField("jetons de sortie max.", default=4000)
    daily_quota = models.PositiveSmallIntegerField("quota par utilisateur et par jour", default=20)
    anonymous_quota = models.PositiveSmallIntegerField(
        "quota par visiteur et par jour", default=0, help_text="0 : réservé aux comptes."
    )

    class Meta:
        ordering = ["feature", "mode"]
        verbose_name = "route"
        constraints = [
            models.UniqueConstraint(fields=["feature", "mode"], name="unique_feature_mode")
        ]

    def __str__(self):
        return f"{self.get_feature_display()} · {self.get_mode_display()}"


class Usage(models.Model):
    created_at = models.DateTimeField("date", auto_now_add=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    feature = models.CharField("fonctionnalité", max_length=20, choices=Feature)
    mode = models.CharField(max_length=10, choices=Mode)
    model = models.ForeignKey(
        AIModel, on_delete=models.SET_NULL, null=True, related_name="+", verbose_name="modèle"
    )
    input_tokens = models.PositiveIntegerField("jetons entrée", default=0)
    output_tokens = models.PositiveIntegerField("jetons sortie", default=0)
    cost = models.DecimalField("coût ($)", max_digits=10, decimal_places=6, default=0)
    duration_ms = models.PositiveIntegerField("durée (ms)", default=0)
    ok = models.BooleanField("réussi", default=True)
    error = models.CharField("erreur", max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "appel"
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "feature", "created_at"]),
        ]

    def __str__(self):
        return f"{self.get_feature_display()} {self.created_at:%d/%m %H:%M}"


class MealPlan(TimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        RUNNING = "running", "En préparation"
        READY = "ready", "Prêt"
        FAILED = "failed", "Échec"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="meal_plans"
    )
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING)
    mode = models.CharField(max_length=10, choices=Mode, default=Mode.FAST)
    days = models.PositiveSmallIntegerField("jours", default=5)
    meals_per_day = models.PositiveSmallIntegerField("repas par jour", default=1)
    servings = models.PositiveSmallIntegerField("personnes", default=2)
    budget = models.DecimalField(
        "budget total (€)", max_digits=7, decimal_places=2, null=True, blank=True
    )
    diet = models.ForeignKey(
        Diet, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="régime"
    )
    use_pantry = models.BooleanField("utiliser le garde-manger", default=True)
    preferences = models.CharField("envies", max_length=300, blank=True)
    summary = models.TextField("résumé", blank=True)
    tips = models.JSONField("conseils", default=list, blank=True)
    is_fallback = models.BooleanField("sans IA", default=False)
    shopping_list = models.ForeignKey(
        "shopping.ShoppingList", on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "menu"

    def __str__(self):
        return f"Menu du {formats.date_format(timezone.localtime(self.created_at), 'j F Y')}"

    def get_absolute_url(self):
        return reverse("assistant:plan", args=[self.pk])


class PlannedMeal(models.Model):
    class Slot(models.TextChoices):
        LUNCH = "lunch", "Déjeuner"
        DINNER = "dinner", "Dîner"

    plan = models.ForeignKey(MealPlan, on_delete=models.CASCADE, related_name="meals")
    day = models.PositiveSmallIntegerField("jour")
    slot = models.CharField("repas", max_length=10, choices=Slot, default=Slot.DINNER)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="+")
    reason = models.CharField("pourquoi", max_length=300, blank=True)

    class Meta:
        ordering = ["day", "-slot", "pk"]
        verbose_name = "repas"

    def __str__(self):
        return f"Jour {self.day} : {self.recipe}"
