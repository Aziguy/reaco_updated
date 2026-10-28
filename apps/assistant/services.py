import logging
import time
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import formats, timezone

from apps.core.ratelimit import client_ip

from .models import Mode, Route, Usage
from .providers import AIError, Prompt, client_for

logger = logging.getLogger(__name__)

DAY = 24 * 3600


class Unavailable(Exception):
    """The assistant cannot answer: the view falls back to the classic feature."""

    def __init__(self, reason: str, message: str):
        super().__init__(message)
        self.reason = reason
        self.message = message


@dataclass
class Caller:
    user: object | None
    ip: str

    @classmethod
    def from_request(cls, request) -> "Caller":
        user = request.user if request.user.is_authenticated else None
        return cls(user, client_ip(request))

    @property
    def key(self) -> str:
        return f"user:{self.user.pk}" if self.user else f"ip:{self.ip}"


def get_route(feature: str, mode: str) -> Route | None:
    routes = Route.objects.select_related("model__provider", "fallback__provider")
    route = routes.filter(feature=feature, mode=mode).first()
    if route is None and mode != Mode.FAST:
        route = routes.filter(feature=feature, mode=Mode.FAST).first()
    return route


def month_spend() -> Decimal:
    def compute():
        start = timezone.localdate().replace(day=1)
        total = Usage.objects.filter(created_at__date__gte=start).aggregate(total=Sum("cost"))
        return total["total"] or Decimal(0)

    return cache.get_or_set("assistant:month-spend", compute, 60)


def spend_summary() -> dict:
    spent = month_spend()
    budget = Decimal(str(settings.AI["MONTHLY_BUDGET_USD"]))
    percent = min(round(100 * spent / budget), 100) if budget else 100
    return {
        "month_spend": spent,
        "budget": budget,
        "budget_percent": percent,
        "budget_label": f"{percent} % de {formats.number_format(budget, 0)} $",
    }


def _counter_key(caller: Caller, feature: str) -> str:
    return f"assistant:quota:{feature}:{caller.key}:{timezone.localdate():%Y%m%d}"


def quota(route: Route, caller: Caller) -> int:
    """Visitor quota, else the daily quota of the user's plan, else the route default."""
    if not caller.user:
        return route.anonymous_quota
    from apps.billing.services import plan_of

    plan = plan_of(caller.user)
    limit = plan.daily_quota(route.feature) if plan else None
    return route.daily_quota if limit is None else limit


def deep_allowed(caller: Caller) -> bool:
    from apps.billing.services import plan_of

    if not caller.user or caller.user.is_staff:
        return True
    plan = plan_of(caller.user)
    return plan is None or plan.deep_mode


def used_today(route: Route, caller: Caller) -> int:
    if caller.user:
        return Usage.objects.filter(
            user=caller.user, feature=route.feature, ok=True, created_at__date=timezone.localdate()
        ).count()
    return cache.get(_counter_key(caller, route.feature), 0)


def remaining(route: Route, caller: Caller) -> int:
    return max(quota(route, caller) - used_today(route, caller), 0)


def availability(feature: str, mode: str, caller: Caller) -> Route:
    """The route to use, or Unavailable with a message for the user."""
    if not settings.AI["ENABLED"]:
        raise Unavailable("disabled", "L'assistant est momentanément indisponible.")
    route = get_route(feature, mode)
    if route is None or not any(m and m.is_available for m in (route.model, route.fallback)):
        raise Unavailable("disabled", "L'assistant est momentanément indisponible.")
    if month_spend() >= Decimal(str(settings.AI["MONTHLY_BUDGET_USD"])):
        raise Unavailable("budget", "L'assistant a atteint son budget du mois.")
    if route.mode == Mode.DEEP and not deep_allowed(caller):
        from apps.billing.services import deep_plan

        plan = deep_plan()
        name = f"la formule {plan}" if plan else "une formule payante"
        raise Unavailable("plan", f"Le mode Approfondi est inclus dans {name}.")
    if quota(route, caller) == 0:
        if caller.user:
            raise Unavailable("quota", "Cette fonction n'est pas incluse dans votre formule.")
        raise Unavailable("login", "Connectez-vous pour utiliser l'assistant.")
    if remaining(route, caller) <= 0:
        raise Unavailable("quota", "Vous avez atteint la limite du jour. Revenez demain !")
    return route


def _record(route, model, caller, started, completion=None, error=""):
    usage = Usage.objects.create(
        user=caller.user,
        feature=route.feature,
        mode=route.mode,
        model=model,
        input_tokens=completion.input_tokens if completion else 0,
        output_tokens=completion.output_tokens if completion else 0,
        cost=model.cost(completion.input_tokens, completion.output_tokens) if completion else 0,
        duration_ms=round((time.monotonic() - started) * 1000),
        ok=completion is not None,
        error=error[:300],
    )
    cache.delete("assistant:month-spend")
    return usage


def ask(feature: str, mode: str, caller: Caller, prompt: Prompt) -> dict:
    """Answer with the route model, then its fallback; counts against the caller's quota."""
    route = availability(feature, mode, caller)
    prompt.effort = route.effort
    prompt.max_tokens = route.max_tokens
    models = [m for m in (route.model, route.fallback) if m and m.is_available]
    if prompt.images:
        models = [m for m in models if m.supports_vision]
    for model in models:
        started = time.monotonic()
        try:
            completion = client_for(model).complete(prompt)
        except AIError as exc:
            logger.warning("Assistant %s via %s failed: %s", feature, model, exc)
            _record(route, model, caller, started, error=str(exc))
            continue
        _record(route, model, caller, started, completion)
        if not caller.user and not cache.add(_counter_key(caller, feature), 1, DAY):
            cache.incr(_counter_key(caller, feature))
        return completion.data
    raise Unavailable("error", "L'assistant ne répond pas pour le moment.")
