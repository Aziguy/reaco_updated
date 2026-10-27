from django.conf import settings
from django.contrib import admin
from django.db.models import Count, Sum

from .models import AIModel, MealPlan, PlannedMeal, Provider, Route, Usage
from .services import month_spend


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "base_url", "api_key_env", "is_configured", "is_active")
    list_editable = ("is_active",)

    @admin.display(boolean=True, description="clé présente")
    def is_configured(self, obj):
        return obj.is_configured


@admin.register(AIModel)
class AIModelAdmin(admin.ModelAdmin):
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
class RouteAdmin(admin.ModelAdmin):
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
class UsageAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "feature",
        "mode",
        "model",
        "user",
        "input_tokens",
        "output_tokens",
        "cost",
        "duration_ms",
        "ok",
    )
    list_filter = ("feature", "mode", "ok", "model")
    date_hierarchy = "created_at"
    search_fields = ("user__email", "error")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        totals = Usage.objects.values("feature").annotate(calls=Count("id"), cost=Sum("cost"))
        extra_context = {
            **(extra_context or {}),
            "month_spend": month_spend(),
            "budget": settings.AI["MONTHLY_BUDGET_USD"],
            "totals": totals.order_by("feature"),
        }
        return super().changelist_view(request, extra_context)


class PlannedMealInline(admin.TabularInline):
    model = PlannedMeal
    raw_id_fields = ("recipe",)
    extra = 0


@admin.register(MealPlan)
class MealPlanAdmin(admin.ModelAdmin):
    list_display = ("__str__", "user", "status", "mode", "days", "servings", "is_fallback")
    list_filter = ("status", "mode", "is_fallback")
    raw_id_fields = ("user", "shopping_list")
    inlines = [PlannedMealInline]
