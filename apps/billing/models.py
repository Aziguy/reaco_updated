import calendar
import secrets
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from apps.assistant.models import Feature

REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


class Period(models.TextChoices):
    MONTH = "month", "Mensuel"
    YEAR = "year", "Annuel"


class Plan(models.Model):
    slug = models.SlugField(max_length=40, unique=True)
    name = models.CharField("nom", max_length=60)
    tagline = models.CharField("accroche", max_length=160, blank=True)
    monthly_price = models.DecimalField(
        "prix mensuel (€)", max_digits=6, decimal_places=2, default=Decimal(0)
    )
    yearly_price = models.DecimalField(
        "prix annuel (€)", max_digits=7, decimal_places=2, default=Decimal(0)
    )
    features = models.TextField("avantages", blank=True, help_text="Un avantage par ligne.")
    deep_mode = models.BooleanField("mode Approfondi", default=False)
    is_default = models.BooleanField(
        "formule par défaut", default=False, help_text="Celle des comptes sans abonnement."
    )
    is_highlighted = models.BooleanField("mise en avant", default=False)
    is_active = models.BooleanField("proposée", default=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)
    stripe_monthly_price = models.CharField(
        "prix Stripe mensuel", max_length=60, blank=True, help_text="Identifiant price_…"
    )
    stripe_yearly_price = models.CharField("prix Stripe annuel", max_length=60, blank=True)

    class Meta:
        ordering = ["position", "monthly_price"]
        verbose_name = "formule"

    def __str__(self):
        return self.name

    @property
    def is_free(self) -> bool:
        return not self.monthly_price and not self.yearly_price

    @property
    def feature_list(self) -> list[str]:
        return [line.strip() for line in self.features.splitlines() if line.strip()]

    @property
    def yearly_per_month(self) -> Decimal:
        return (self.yearly_price / 12).quantize(Decimal("0.01"))

    @property
    def yearly_saving(self) -> Decimal:
        return max(self.monthly_price * 12 - self.yearly_price, Decimal(0))

    def price(self, period: str) -> Decimal:
        return self.yearly_price if period == Period.YEAR else self.monthly_price

    def stripe_price(self, period: str) -> str:
        return self.stripe_yearly_price if period == Period.YEAR else self.stripe_monthly_price

    @property
    def ordered_quotas(self) -> list["PlanQuota"]:
        order = {feature: index for index, feature in enumerate(Feature.values)}
        return sorted(self.quotas.all(), key=lambda quota: order.get(quota.feature, 99))

    def daily_quota(self, feature: str) -> int | None:
        quota = next((q for q in self.quotas.all() if q.feature == feature), None)
        return quota.daily if quota else None


class PlanQuota(models.Model):
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="quotas")
    feature = models.CharField("fonctionnalité", max_length=20, choices=Feature)
    daily = models.PositiveSmallIntegerField("par jour")

    class Meta:
        ordering = ["plan", "feature"]
        verbose_name = "quota"
        constraints = [
            models.UniqueConstraint(fields=["plan", "feature"], name="unique_plan_feature")
        ]

    def __str__(self):
        return f"{self.get_feature_display()} : {self.daily} / jour"


def add_period(start: date, period: str) -> date:
    """Last day covered by a period starting on `start`."""
    months = 12 if period == Period.YEAR else 1
    month = start.month - 1 + months
    year, month = start.year + month // 12, month % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day) - timedelta(days=1)


def new_reference() -> str:
    while True:
        reference = "CG-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))
        if not Subscription.objects.filter(reference=reference).exists():
            return reference


class SubscriptionQuerySet(models.QuerySet):
    def current(self):
        return self.filter(status=Subscription.Status.ACTIVE, ends_on__gte=timezone.localdate())


class Subscription(models.Model):
    class Method(models.TextChoices):
        TRANSFER = "transfer", "Virement bancaire"
        WERO = "wero", "Wero"
        STRIPE = "stripe", "Carte bancaire"

    class Status(models.TextChoices):
        PENDING = "pending", "En attente de paiement"
        ACTIVE = "active", "Active"
        CANCELED = "canceled", "Annulée"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="subscriptions",
        verbose_name="utilisateur",
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, verbose_name="formule")
    period = models.CharField("période", max_length=10, choices=Period, default=Period.MONTH)
    method = models.CharField("paiement", max_length=10, choices=Method)
    status = models.CharField("statut", max_length=10, choices=Status, default=Status.PENDING)
    reference = models.CharField("référence", max_length=12, unique=True, default=new_reference)
    amount = models.DecimalField("montant (€)", max_digits=7, decimal_places=2)
    starts_on = models.DateField("début", null=True, blank=True)
    ends_on = models.DateField("fin", null=True, blank=True)
    declared_at = models.DateTimeField("paiement signalé le", null=True, blank=True)
    confirmed_at = models.DateTimeField("confirmé le", null=True, blank=True)
    stripe_customer = models.CharField("client Stripe", max_length=60, blank=True)
    stripe_subscription = models.CharField(
        "abonnement Stripe", max_length=60, blank=True, db_index=True
    )
    note = models.CharField("note interne", max_length=300, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = SubscriptionQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-pk"]
        verbose_name = "abonnement"

    def __str__(self):
        return f"{self.reference} · {self.plan} ({self.get_period_display().lower()})"

    def get_absolute_url(self):
        return reverse("billing:payment", args=[self.reference])

    @property
    def is_current(self) -> bool:
        return (
            self.status == self.Status.ACTIVE
            and self.ends_on is not None
            and self.ends_on >= timezone.localdate()
        )

    @property
    def monthly_amount(self) -> Decimal:
        return self.amount / 12 if self.period == Period.YEAR else self.amount

    @property
    def days_left(self) -> int | None:
        return (self.ends_on - timezone.localdate()).days if self.ends_on else None


class PaymentSettings(models.Model):
    transfer_enabled = models.BooleanField("virement proposé", default=False)
    account_holder = models.CharField("titulaire du compte", max_length=120, blank=True)
    iban = models.CharField("IBAN", max_length=40, blank=True)
    bic = models.CharField("BIC", max_length=11, blank=True)
    bank_name = models.CharField("banque", max_length=120, blank=True)
    wero_enabled = models.BooleanField("Wero proposé", default=False)
    wero_name = models.CharField("nom affiché dans Wero", max_length=120, blank=True)
    wero_handle = models.CharField(
        "téléphone ou email Wero", max_length=120, blank=True, help_text="Ex. 06 12 34 56 78"
    )
    stripe_enabled = models.BooleanField(
        "carte bancaire (Stripe) proposée",
        default=False,
        help_text="Nécessite STRIPE_SECRET_KEY et STRIPE_WEBHOOK_SECRET dans l'environnement.",
    )
    notice = models.TextField(
        "message aux abonnés",
        blank=True,
        help_text="Affiché sur la page de paiement, par ex. le délai d'activation.",
    )

    class Meta:
        verbose_name = "réglages de paiement"
        verbose_name_plural = "réglages de paiement"

    def __str__(self):
        return "Réglages de paiement"

    @classmethod
    def load(cls) -> "PaymentSettings":
        return cls.objects.get_or_create(pk=1)[0]

    @property
    def iban_display(self) -> str:
        compact = self.iban.replace(" ", "").upper()
        return " ".join(compact[i : i + 4] for i in range(0, len(compact), 4))

    @property
    def transfer_ready(self) -> bool:
        return self.transfer_enabled and bool(self.iban and self.account_holder)

    @property
    def wero_ready(self) -> bool:
        return self.wero_enabled and bool(self.wero_handle)


class Expense(models.Model):
    class Category(models.TextChoices):
        HOSTING = "hosting", "Hébergement"
        DOMAIN = "domain", "Nom de domaine"
        AI = "ai", "Intelligence artificielle"
        DEVELOPMENT = "development", "Développement et maintenance"
        MARKETING = "marketing", "Communication et réseaux sociaux"
        OTHER = "other", "Autres frais"

    label = models.CharField("libellé", max_length=120)
    category = models.CharField("catégorie", max_length=20, choices=Category)
    monthly_amount = models.DecimalField("montant mensuel (€)", max_digits=8, decimal_places=2)
    note = models.CharField("précision publique", max_length=200, blank=True)
    is_active = models.BooleanField("affiché", default=True)
    position = models.PositiveSmallIntegerField("ordre", default=0)

    class Meta:
        ordering = ["position", "pk"]
        verbose_name = "frais"
        verbose_name_plural = "frais"

    def __str__(self):
        return self.label
