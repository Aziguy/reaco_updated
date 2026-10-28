import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Prefetch
from django.urls import reverse
from django.utils import timezone

from .models import Expense, Period, Plan, PlanQuota, Subscription, add_period

logger = logging.getLogger(__name__)
CENT = Decimal("0.01")


def plans():
    return Plan.objects.filter(is_active=True).prefetch_related(
        Prefetch("quotas", PlanQuota.objects.order_by("feature"))
    )


def current_subscription(user) -> Subscription | None:
    if not user or not user.is_authenticated:
        return None
    return (
        Subscription.objects.current()
        .filter(user=user)
        .select_related("plan")
        .order_by("-ends_on")
        .first()
    )


def plan_of(user) -> Plan | None:
    """The plan whose quotas apply: the current subscription, else the default plan."""
    subscription = current_subscription(user)
    if subscription:
        return subscription.plan
    return Plan.objects.filter(is_default=True).prefetch_related("quotas").first()


def deep_plan() -> Plan | None:
    return Plan.objects.filter(is_active=True, deep_mode=True).order_by("monthly_price").first()


@transaction.atomic
def start(user, plan: Plan, period: str, method: str) -> Subscription:
    """A pending subscription, reused while the same request is still unpaid."""
    pending = Subscription.objects.filter(
        user=user, plan=plan, period=period, method=method, status=Subscription.Status.PENDING
    ).first()
    if pending:
        return pending
    return Subscription.objects.create(
        user=user, plan=plan, period=period, method=method, amount=plan.price(period)
    )


def declare(subscription: Subscription) -> None:
    if subscription.declared_at:
        return
    subscription.declared_at = timezone.now()
    subscription.save(update_fields=["declared_at", "updated_at"])
    admin_url = reverse("admin:billing_subscription_change", args=[subscription.pk])
    send_mail(
        f"Paiement signalé {subscription.reference}",
        f"{subscription.user.email} indique avoir payé {subscription.amount} € par "
        f"{subscription.get_method_display().lower()} pour la formule {subscription.plan} "
        f"({subscription.get_period_display().lower()}).\n\nÀ vérifier : {admin_url}",
        settings.DEFAULT_FROM_EMAIL,
        [settings.CONTACT_EMAIL],
        fail_silently=True,
    )


@transaction.atomic
def activate(subscription: Subscription, *, ends_on=None) -> Subscription:
    """Start after any current subscription so that a renewal adds up."""
    today = timezone.localdate()
    if subscription.status == Subscription.Status.ACTIVE and ends_on is None:
        return subscription
    latest = (
        Subscription.objects.current()
        .filter(user=subscription.user)
        .exclude(pk=subscription.pk)
        .order_by("-ends_on")
        .first()
    )
    starts_on = latest.ends_on + timedelta(days=1) if latest else today
    subscription.status = Subscription.Status.ACTIVE
    subscription.starts_on = subscription.starts_on or starts_on
    subscription.ends_on = ends_on or add_period(subscription.starts_on, subscription.period)
    subscription.confirmed_at = subscription.confirmed_at or timezone.now()
    subscription.save()
    send_mail(
        f"Votre formule {subscription.plan} est active",
        f"Bonjour,\n\nMerci pour votre soutien ! Votre formule {subscription.plan} est active "
        f"jusqu'au {subscription.ends_on:%d/%m/%Y}.\n\nL'équipe {settings.SITE_NAME}",
        settings.DEFAULT_FROM_EMAIL,
        [subscription.user.email],
        fail_silently=True,
    )
    return subscription


def cancel(subscription: Subscription) -> None:
    subscription.status = Subscription.Status.CANCELED
    if subscription.ends_on and subscription.ends_on > timezone.localdate():
        subscription.ends_on = timezone.localdate()
    subscription.save(update_fields=["status", "ends_on", "updated_at"])


@dataclass
class CostLine:
    label: str
    category: str
    amount: Decimal
    note: str = ""
    measured: bool = False
    share: int = 0


@dataclass
class Costs:
    lines: list[CostLine]
    revenue: Decimal
    subscribers: int

    @property
    def total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal(0))

    @property
    def coverage(self) -> int:
        return min(round(100 * self.revenue / self.total), 100) if self.total else 0


def monthly_costs() -> Costs:
    """This month's costs, the measured AI spend included, and their coverage by subscriptions."""
    from apps.assistant.services import month_spend

    lines = [
        CostLine(e.label, e.category, e.monthly_amount, e.note)
        for e in Expense.objects.filter(is_active=True)
    ]
    rate = Decimal(str(settings.BILLING["USD_TO_EUR"]))
    ai = (month_spend() * rate).quantize(CENT)
    lines.append(
        CostLine(
            "Assistant IA",
            Expense.Category.AI,
            ai,
            "Mesuré sur les appels du mois en cours.",
            measured=True,
        )
    )
    current = Subscription.objects.current().filter(amount__gt=0)
    revenue = sum((s.monthly_amount for s in current), Decimal(0)).quantize(CENT)
    costs = Costs(lines, revenue, current.values("user").distinct().count())
    for line in costs.lines:
        line.share = round(100 * line.amount / costs.total) if costs.total else 0
    return costs


def period_label(period: str) -> str:
    return "an" if period == Period.YEAR else "mois"
