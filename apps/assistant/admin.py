from django.contrib import admin
from django.db.models import Count, Sum
from unfold.admin import ModelAdmin, TabularInline

from .models import AIModel, Feature, MealPlan, PlannedMeal, Provider, Route, Usage
from .services import spend_summary


@admin.register(Provider)
class ProviderAdmin(ModelAdmin):
    list_display = ("name", "kind", "base_url", "api_key_env", "is_configured", "is_active")
    list_editable = ("is_active",)

    @admin.display(boolean=True, description="clé présente")
    def is_configured(self, obj):
        return obj.is_configured


@admin.register(AIModel)
class AIModelAdmin(ModelAdmin):
    list_display = (
        "label",
        "model_id",
        "provider",
        "supports_vision",
        "supports_effort",
        "input_price",
        "output_price",
        "is_active",
    )
    list_filter = ("provider", "is_active")
    list_editable = ("is_active",)


@admin.register(Route)
class RouteAdmin(ModelAdmin):
    list_display = (
        "__str__",
        "model",
        "fallback",
        "effort",
        "max_tokens",
        "daily_quota",
        "anonymous_quota",
    )
    list_editable = ("model", "fallback", "effort", "max_tokens", "daily_quota", "anonymous_quota")
    list_filter = ("feature", "mode")


@admin.register(Usage)
class UsageAdmin(ModelAdmin):
    list_display = (
        "created_at",
        "feature",
        "mode",
        "model_label",
        "user",
        "input_tokens",
        "output_tokens",
        "cost",
        "duration_ms",
        "ok",
    )
    list_filter = ("feature", "mode", "ok", "model")
    list_select_related = ("model", "user")
    date_hierarchy = "created_at"
    search_fields = ("user__email", "error")
    list_before_template = "admin/assistant/usage/summary.html"

    @admin.display(description="modèle", ordering="model__label")
    def model_label(self, obj):
        return obj.model.label if obj.model else ""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        totals = Usage.objects.values("feature").annotate(calls=Count("id"), cost=Sum("cost"))
        totals = totals.order_by("feature")
        totals = [
            {**row, "label": Feature(row["feature"]).label} for row in totals.order_by("feature")
        ]
        extra_context = {**(extra_context or {}), **spend_summary(), "totals": totals}
        return super().changelist_view(request, extra_context)


class PlannedMealInline(TabularInline):
    model = PlannedMeal
    raw_id_fields = ("recipe",)
    extra = 0


@admin.register(MealPlan)
class MealPlanAdmin(ModelAdmin):
    list_display = ("__str__", "user", "status", "mode", "days", "servings", "is_fallback")
    list_filter = ("status", "mode", "is_fallback")
    raw_id_fields = ("user", "shopping_list")
    inlines = [PlannedMealInline]
