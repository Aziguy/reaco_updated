from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from . import services
from .models import Expense, PaymentSettings, Plan, PlanQuota, Subscription


class PlanQuotaInline(TabularInline):
    model = PlanQuota
    extra = 0
    tab = True


@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = (
        "name", "monthly_price", "yearly_price", "deep_mode", "is_default", "is_active", "position",
    )  # fmt: skip
    list_editable = ("position",)
    prepopulated_fields = {"slug": ("name",)}
    inlines = (PlanQuotaInline,)
    fieldsets = (
        (None, {"fields": ("name", "slug", "tagline", "features"), "classes": ["tab"]}),
        (
            "Prix",
            {
                "fields": ("monthly_price", "yearly_price", "deep_mode"),
                "classes": ["tab"],
            },
        ),
        (
            "Affichage",
            {
                "fields": ("is_default", "is_highlighted", "is_active", "position"),
                "classes": ["tab"],
            },
        ),
        (
            "Stripe",
            {"fields": ("stripe_monthly_price", "stripe_yearly_price"), "classes": ["tab"]},
        ),
    )


@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = (
        "reference", "user", "plan", "period", "method", "amount", "state", "ends_on",
        "declared_at",
    )  # fmt: skip
    list_filter = ("status", "method", "plan", "period")
    search_fields = ("reference", "user__email")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at", "confirmed_at", "declared_at")
    actions = ("confirm_payment", "cancel")
    date_hierarchy = "created_at"

    @display(
        description="statut",
        label={
            Subscription.Status.PENDING: "warning",
            Subscription.Status.ACTIVE: "success",
            Subscription.Status.CANCELED: "danger",
        },
    )
    def state(self, obj):
        return obj.status, obj.get_status_display()

    @admin.action(description="Confirmer la réception du paiement")
    def confirm_payment(self, request, queryset):
        pending = queryset.filter(status=Subscription.Status.PENDING)
        for subscription in pending.select_related("user", "plan"):
            services.activate(subscription)
        self.message_user(request, f"{pending.count()} abonnement(s) activé(s).")

    @admin.action(description="Annuler")
    def cancel(self, request, queryset):
        for subscription in queryset:
            services.cancel(subscription)
        self.message_user(request, f"{queryset.count()} abonnement(s) annulé(s).")


@admin.register(PaymentSettings)
class PaymentSettingsAdmin(ModelAdmin):
    fieldsets = (
        (
            "Virement",
            {
                "fields": ("transfer_enabled", "account_holder", "iban", "bic", "bank_name"),
                "classes": ["tab"],
            },
        ),
        ("Wero", {"fields": ("wero_enabled", "wero_name", "wero_handle"), "classes": ["tab"]}),
        ("Carte bancaire", {"fields": ("stripe_enabled",), "classes": ["tab"]}),
        ("Message", {"fields": ("notice",), "classes": ["tab"]}),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        settings = PaymentSettings.load()
        return redirect(reverse("admin:billing_paymentsettings_change", args=[settings.pk]))


@admin.register(Expense)
class ExpenseAdmin(ModelAdmin):
    list_display = ("label", "category", "monthly_amount", "is_active", "position")
    list_editable = ("monthly_amount", "is_active", "position")
    list_filter = ("category", "is_active")
