from allauth.mfa.models import Authenticator
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Exists, OuterRef
from unfold.admin import ModelAdmin
from unfold.decorators import display
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import User

MFA_LABELS = {
    Authenticator.Type.TOTP: "application d'authentification",
    Authenticator.Type.WEBAUTHN: "clé d'accès",
    Authenticator.Type.RECOVERY_CODES: "codes de secours",
}


class MFAFilter(admin.SimpleListFilter):
    title = "double authentification"
    parameter_name = "mfa"

    def lookups(self, request, model_admin):
        return (("1", "Active"), ("0", "Inactive"))

    def queryset(self, request, queryset):
        if self.value() in ("0", "1"):
            return queryset.filter(has_mfa=self.value() == "1")
        return queryset


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "city", "mfa", "is_staff", "date_joined")
    list_filter = (MFAFilter, "is_staff", "is_active")
    search_fields = ("email", "first_name", "last_name", "city")
    readonly_fields = ("mfa_methods",)
    actions = ("reset_mfa",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identité", {"fields": ("first_name", "last_name", "household_size")}),
        (
            "Localisation",
            {"fields": ("postal_code", "city", "latitude", "longitude", "search_radius_km")},
        ),
        ("Préférences", {"fields": ("expiry_reminders",)}),
        ("Sécurité", {"fields": ("mfa_methods",)}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)

    def get_queryset(self, request):
        authenticators = Authenticator.objects.filter(user=OuterRef("pk"))
        return super().get_queryset(request).annotate(has_mfa=Exists(authenticators))

    @display(description="2FA", label={True: "success", False: "warning"})
    def mfa(self, obj):
        enabled = getattr(obj, "has_mfa", None)
        if enabled is None:
            enabled = Authenticator.objects.filter(user=obj).exists()
        return enabled, "Active" if enabled else "Inactive"

    @admin.display(description="double authentification")
    def mfa_methods(self, obj):
        types = Authenticator.objects.filter(user=obj).values_list("type", flat=True)
        return ", ".join(sorted({MFA_LABELS.get(t, t) for t in types})) or "Inactive"

    @admin.action(description="Réinitialiser la double authentification")
    def reset_mfa(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, "Réservé aux super-utilisateurs.", level="error")
            return
        deleted, _ = Authenticator.objects.filter(user__in=queryset).delete()
        self.message_user(request, f"{deleted} méthode(s) supprimée(s).")
