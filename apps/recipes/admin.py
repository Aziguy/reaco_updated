from django.contrib import admin
from django.utils.html import format_html

from . import metrics
from .models import Diet, Ingredient, Recipe, RecipeIngredient, RecipeStep


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "aisle", "price_unit", "off_category", "impactco2_slug", "is_staple")
    list_filter = ("aisle", "price_unit", "is_staple")
    search_fields = ("name", "off_category")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Diet)
class DietAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    autocomplete_fields = ("ingredient",)
    extra = 1


class RecipeStepInline(admin.TabularInline):
    model = RecipeStep
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
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
    list_filter = ("course", "difficulty", "diets", "is_featured", "is_published")
    list_editable = ("is_featured", "is_published")
    search_fields = ("title", "origin")
    prepopulated_fields = {"slug": ("title",)}
    filter_horizontal = ("diets",)
    readonly_fields = (
        "cost_per_serving",
        "price_coverage",
        "co2_per_serving",
        "metrics_updated_at",
    )
    inlines = (RecipeIngredientInline, RecipeStepInline)
    actions = ("refresh_metrics",)

    @admin.display(description="")
    def thumbnail(self, obj):
        if not obj.image:
            return ""
        return format_html(
            '<img src="{}" width="48" height="48" style="object-fit:cover;border-radius:8px">',
            obj.image.url,
        )

    @admin.action(description="Recalculer coût et empreinte carbone")
    def refresh_metrics(self, request, queryset):
        for recipe in queryset.with_relations():
            metrics.refresh(recipe)
        self.message_user(request, f"{queryset.count()} recette(s) mise(s) à jour.")
