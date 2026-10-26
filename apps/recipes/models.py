from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from apps.core.models import TimeStampedModel
from apps.core.text import make_slug, normalize

from .units import BaseUnit, Unit, format_quantity, unit_label


class Aisle(models.TextChoices):
    PRODUCE = "produce", "Fruits et légumes"
    MEAT = "meat", "Boucherie"
    FISH = "fish", "Poissonnerie"
    DAIRY = "dairy", "Crèmerie"
    CHEESE = "cheese", "Fromagerie"
    GROCERY = "grocery", "Épicerie"
    SPICES = "spices", "Épices et condiments"
    BAKERY = "bakery", "Boulangerie"
    DRINKS = "drinks", "Boissons"
    OTHER = "other", "Autre"


class Ingredient(models.Model):
    name = models.CharField("nom", max_length=100, unique=True)
    slug = models.SlugField(max_length=110, unique=True)
    aisle = models.CharField("rayon", max_length=20, choices=Aisle, default=Aisle.OTHER)
    price_unit = models.CharField(
        "unité de prix", max_length=5, choices=BaseUnit, default=BaseUnit.KILOGRAM
    )
    unit_weight_g = models.DecimalField(
        "poids d'une pièce (g)", max_digits=7, decimal_places=1, null=True, blank=True
    )
    off_category = models.CharField(
        "catégorie Open Food Facts",
        max_length=120,
        blank=True,
        help_text="Taxonomie Open Food Facts, par ex. en:tomatoes.",
    )
    impactco2_slug = models.CharField("aliment ADEME", max_length=60, blank=True)
    ciqual_code = models.CharField(
        "code CIQUAL", max_length=10, blank=True, help_text="Aliment de la table Ciqual de l'Anses."
    )
    kcal_100g = models.DecimalField(
        "kcal / 100 g", max_digits=6, decimal_places=1, null=True, blank=True
    )
    proteins_100g = models.DecimalField(
        "protéines / 100 g", max_digits=5, decimal_places=2, null=True, blank=True
    )
    fat_100g = models.DecimalField(
        "lipides / 100 g", max_digits=5, decimal_places=2, null=True, blank=True
    )
    carbs_100g = models.DecimalField(
        "glucides / 100 g", max_digits=5, decimal_places=2, null=True, blank=True
    )
    is_staple = models.BooleanField(
        "produit de base", default=False, help_text="Sel, poivre, huile : supposé disponible."
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "ingrédient"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.name)
        super().save(*args, **kwargs)


class Diet(models.Model):
    name = models.CharField("nom", max_length=60, unique=True)
    slug = models.SlugField(max_length=70, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "régime"

    def __str__(self):
        return self.name


class RecipeQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def with_relations(self):
        return self.select_related("author").prefetch_related(
            "diets", models.Prefetch("items", RecipeIngredient.objects.select_related("ingredient"))
        )


class Recipe(TimeStampedModel):
    class Course(models.TextChoices):
        STARTER = "starter", "Entrée"
        MAIN = "main", "Plat principal"
        SALAD = "salad", "Salade"
        SOUP = "soup", "Soupe"
        DESSERT = "dessert", "Dessert"
        BREAKFAST = "breakfast", "Petit déjeuner"
        SNACK = "snack", "En-cas"
        SAUCE = "sauce", "Sauce"
        DRINK = "drink", "Boisson"

    class Difficulty(models.IntegerChoices):
        VERY_EASY = 1, "Très facile"
        EASY = 2, "Facile"
        MEDIUM = 3, "Intermédiaire"
        HARD = 4, "Expert"

    title = models.CharField("titre", max_length=200)
    slug = models.SlugField(max_length=220, unique=True)
    summary = models.TextField("résumé", max_length=500, blank=True)
    course = models.CharField("type de plat", max_length=20, choices=Course, default=Course.MAIN)
    difficulty = models.PositiveSmallIntegerField(
        "difficulté", choices=Difficulty, default=Difficulty.EASY
    )
    servings = models.PositiveSmallIntegerField(
        "portions", default=4, validators=[MinValueValidator(1)]
    )
    prep_minutes = models.PositiveSmallIntegerField("préparation (min)", default=0)
    cook_minutes = models.PositiveSmallIntegerField("cuisson (min)", default=0)
    origin = models.CharField("origine", max_length=120, blank=True)
    diets = models.ManyToManyField(Diet, blank=True, related_name="recipes", verbose_name="régimes")
    image = models.ImageField(upload_to="recipes/", blank=True)
    image_credit = models.CharField("auteur de l'image", max_length=200, blank=True)
    image_license = models.CharField("licence de l'image", max_length=60, blank=True)
    image_license_url = models.URLField("lien de la licence", blank=True)
    image_source = models.URLField("source de l'image", blank=True)
    kcal = models.PositiveSmallIntegerField("kcal / portion", null=True, editable=False)
    proteins_g = models.PositiveSmallIntegerField("protéines (g)", null=True, editable=False)
    fat_g = models.PositiveSmallIntegerField("lipides (g)", null=True, editable=False)
    carbs_g = models.PositiveSmallIntegerField("glucides (g)", null=True, editable=False)
    nutrition_coverage = models.PositiveSmallIntegerField(
        "couverture nutritionnelle (%)", default=0, editable=False
    )
    is_featured = models.BooleanField("mise en avant", default=False)
    is_published = models.BooleanField("publiée", default=True)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    cost_per_serving = models.DecimalField(
        "coût / portion (€)", max_digits=7, decimal_places=2, null=True, blank=True, editable=False
    )
    price_coverage = models.PositiveSmallIntegerField(
        "couverture prix (%)", default=0, editable=False
    )
    co2_per_serving = models.DecimalField(
        "kg CO2e / portion", max_digits=7, decimal_places=3, null=True, blank=True, editable=False
    )
    metrics_updated_at = models.DateTimeField(null=True, blank=True, editable=False)
    search_text = models.TextField(blank=True, editable=False)

    objects = RecipeQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "recette"
        indexes = [models.Index(fields=["is_published", "course"])]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = make_slug(self.title)
        update_fields = kwargs.get("update_fields")
        if update_fields is None or "search_text" in update_fields:
            self.search_text = self.build_search_text()
        super().save(*args, **kwargs)

    def build_search_text(self) -> str:
        parts = [self.title, self.summary, self.origin, self.get_course_display()]
        if self.pk:
            parts += self.items.values_list("ingredient__name", flat=True)
            parts += self.diets.values_list("name", flat=True)
        return normalize(" ".join(parts))

    def refresh_search(self):
        self.save(update_fields=["search_text"])

    def get_absolute_url(self):
        return reverse("recipes:detail", args=[self.slug])

    @property
    def total_minutes(self) -> int:
        return self.prep_minutes + self.cook_minutes


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="items")
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.PROTECT, related_name="recipe_items"
    )
    quantity = models.DecimalField(
        "quantité", max_digits=8, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField("unité", max_length=10, choices=Unit, default=Unit.GRAM)
    note = models.CharField("précision", max_length=120, blank=True)
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "ingrédient de recette"

    def __str__(self):
        return f"{self.display_quantity()} {self.ingredient}".strip()

    def scaled(self, factor: Decimal) -> Decimal | None:
        return None if self.quantity is None else self.quantity * factor

    def display_quantity(self, factor: Decimal = Decimal(1)) -> str:
        quantity = self.scaled(factor)
        if quantity is None:
            return ""
        if self.unit == Unit.PIECE:
            quantity = max((quantity * 2).quantize(Decimal(1)) / 2, Decimal("0.5"))
        return f"{format_quantity(quantity)} {unit_label(self.unit, quantity)}"


class RecipeStep(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="steps")
    position = models.PositiveSmallIntegerField(default=0)
    text = models.TextField("instruction")

    class Meta:
        ordering = ["position", "id"]
        verbose_name = "étape"

    def __str__(self):
        return f"{self.position}. {self.text[:40]}"


class Favorite(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites"
    )
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name="favorites")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "recipe"], name="unique_favorite")]
        verbose_name = "favori"

    def __str__(self):
        return f"{self.user} : {self.recipe}"
