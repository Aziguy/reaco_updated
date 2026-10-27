from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.widgets import UnfoldAdminTextareaWidget

from . import metrics
from .models import Diet, Ingredient, Recipe, RecipeIngredient, RecipeStep


@admin.register(Ingredient)
class IngredientAdmin(ModelAdmin):
    list_display = ("name", "aisle", "price_unit", "off_category", "ciqual_code", "kcal_100g")
    list_filter = ("aisle", "price_unit", "is_staple")
    search_fields = ("name", "off_category")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Diet)
class DietAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class RecipeIngredientInline(TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ("ingredient",)
    verbose_name_plural = "ingrédients"
    extra = 1
    tab = True


class RecipeStepInline(TabularInline):
    model = RecipeStep
    extra = 1
    tab = True
    formfield_overrides = {
        models.TextField: {"widget": UnfoldAdminTextareaWidget(attrs={"rows": 3})}
    }


@admin.register(Recipe)
class RecipeAdmin(ModelAdmin):
    list_display = (
        "thumbnail",
        "title",
        "course",
        "difficulty",
        "servings",
        "cost_per_serving",
        "co2_per_serving",
        "is_featured",
        "is_published",
    )
    list_display_links = ("thumbnail", "title")
    list_filter = (
        "course",
        "difficulty",
        "diets",
        "is_featured",
        "is_published",
        "is_ai_generated",
        "review_requested",
    )
    list_editable = ("is_featured", "is_published")
    search_fields = ("title", "origin")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("diets",)
    raw_id_fields = ("author",)
    fieldsets = (
        (
            "Recette",
            {
                "classes": ["tab"],
                "fields": (
                    ("title", "slug"),
                    "summary",
                    ("course", "difficulty"),
                    ("servings", "prep_minutes", "cook_minutes"),
                    "origin",
                    "diets",
                ),
            },
        ),
        (
            "Image",
            {
                "classes": ["tab"],
                "fields": (
                    "image",
                    ("image_credit", "image_license"),
                    ("image_license_url", "image_source"),
                ),
            },
        ),
        (
            "Publication",
            {
                "classes": ["tab"],
                "fields": (
                    ("is_published", "is_featured"),
                    ("is_ai_generated", "review_requested"),
                    "author",
                ),
            },
        ),
        (
            "Chiffres calculés",
            {
                "classes": ["tab"],
                "fields": (
                    ("cost_per_serving", "price_coverage", "co2_per_serving"),
                    ("kcal", "proteins_g", "fat_g", "carbs_g"),
                    ("nutrition_coverage", "metrics_updated_at"),
                ),
            },
        ),
    )
    readonly_fields = (
        "cost_per_serving",
        "price_coverage",
        "co2_per_serving",
        "kcal",
        "proteins_g",
        "fat_g",
        "carbs_g",
        "nutrition_coverage",
        "metrics_updated_at",
    )
    inlines = (RecipeIngredientInline, RecipeStepInline)
    actions = ("refresh_metrics", "publish")

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        metrics.refresh(Recipe.objects.with_relations().get(pk=form.instance.pk))

    @admin.display(description="")
    def thumbnail(self, obj):
        if not obj.image:
            return ""
        return format_html(
            '<img src="{}" width="48" height="48" style="object-fit:cover;border-radius:8px">',
            obj.image.url,
        )

    @admin.action(description="Publier les recettes sélectionnées")
    def publish(self, request, queryset):
        count = queryset.update(is_published=True, review_requested=False)
        self.message_user(request, f"{count} recette(s) publiée(s).")

    @admin.action(description="Recalculer coût, empreinte carbone et nutrition")
    def refresh_metrics(self, request, queryset):
        for recipe in queryset.with_relations():
            metrics.refresh(recipe)
        self.message_user(request, f"{queryset.count()} recette(s) mise(s) à jour.")
