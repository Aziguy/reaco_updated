from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.assistant.models import Feature
from apps.assistant.services import Caller, get_route, used_today

from . import services, stripe_gateway
from .models import PaymentSettings, Period, Plan, Subscription

FAQ = [
    (
        "Pourquoi un abonnement ?",
        "Comégusto ne cherche pas à faire de bénéfice. L'assistant IA, l'hébergement, le nom de "
        "domaine, le développement et la communication ont un coût : les formules payantes les "
        "couvrent, et tout le reste du site reste gratuit.",
    ),
    (
        "Que se passe-t-il à la fin de ma formule ?",
        "Rien n'est prélevé automatiquement pour un virement ou un paiement Wero : votre compte "
        "revient simplement à la formule Gratuit. Vous pouvez renouveler à tout moment, la "
        "nouvelle période s'ajoute à la précédente.",
    ),
    (
        "Combien de temps pour l'activation ?",
        "Un virement met en général un à trois jours ouvrés à arriver, Wero quelques secondes. "
        "Nous activons votre formule dès réception et vous prévenons par email.",
    ),
    (
        "Puis-je changer de formule ?",
        "Oui. Choisissez la nouvelle formule : elle prend le relais à la fin de la formule en "
        "cours.",
    ),
]


def _methods(payment: PaymentSettings) -> list[tuple[str, str, str]]:
    methods = []
    if payment.transfer_ready:
        methods.append((Subscription.Method.TRANSFER, "Virement bancaire", "1 à 3 jours ouvrés"))
    if payment.wero_ready:
        methods.append((Subscription.Method.WERO, "Wero", "Instantané, depuis votre banque"))
    if stripe_gateway.enabled(payment):
        methods.append((Subscription.Method.STRIPE, "Carte bancaire", "Renouvellement automatique"))
    return methods


def _period(value) -> str:
    return Period.YEAR if value in (Period.YEAR, "an") else Period.MONTH


def pricing(request):
    payment = PaymentSettings.load()
    current = services.current_subscription(request.user)
    context = {
        "plans": services.plans(),
        "current_plan": services.plan_of(request.user) if request.user.is_authenticated else None,
        "current": current,
        "methods": _methods(payment),
        "faq": FAQ,
        "period": _period(request.GET.get("periode")),
    }
    return render(request, "billing/pricing.html", context)


@login_required
def checkout(request, slug):
    plan = get_object_or_404(Plan, slug=slug, is_active=True)
    if plan.is_free:
        return redirect("billing:pricing")
    payment = PaymentSettings.load()
    methods = _methods(payment)
    period = _period(request.POST.get("period") or request.GET.get("periode"))
    if request.method == "POST":
        method = request.POST.get("method")
        if method not in {m[0] for m in methods}:
            messages.error(request, "Choisissez un moyen de paiement.")
        else:
            subscription = services.start(request.user, plan, period, method)
            if method != Subscription.Method.STRIPE:
                return redirect(subscription)
            try:
                return redirect(stripe_gateway.checkout_url(subscription, request))
            except stripe_gateway.StripeError as exc:
                messages.error(request, str(exc))
    context = {
        "plan": plan,
        "period": period,
        "methods": methods,
        "current": services.current_subscription(request.user),
    }
    return render(request, "billing/checkout.html", context)


def _own(request, reference) -> Subscription:
    return get_object_or_404(
        Subscription.objects.select_related("plan"), reference=reference, user=request.user
    )


@login_required
def payment(request, reference):
    subscription = _own(request, reference)
    if subscription.method == Subscription.Method.STRIPE:
        return redirect("billing:account")
    return render(
        request,
        "billing/payment.html",
        {"subscription": subscription, "payment": PaymentSettings.load()},
    )


@login_required
@require_POST
def declare(request, reference):
    subscription = _own(request, reference)
    if subscription.status == Subscription.Status.PENDING:
        services.declare(subscription)
        messages.success(request, "Merci ! Nous activons votre formule dès réception du paiement.")
    return redirect(subscription)


@login_required
@require_POST
def withdraw(request, reference):
    subscription = _own(request, reference)
    if subscription.status == Subscription.Status.PENDING:
        subscription.status = Subscription.Status.CANCELED
        subscription.save(update_fields=["status", "updated_at"])
        messages.success(request, "Demande annulée.")
    return redirect("billing:account")


def _usage(user, plan) -> list[dict]:
    caller = Caller(user, "")
    rows = []
    features = (Feature.SEARCH, Feature.RECIPE, Feature.PHOTO, Feature.RECEIPT, Feature.PLANNER)
    for feature in features:
        route = get_route(feature, "fast")
        if route is None:
            continue
        limit = plan.daily_quota(feature) if plan else None
        limit = route.daily_quota if limit is None else limit
        used = min(used_today(route, caller), limit)
        rows.append(
            {
                "label": Feature(feature).label,
                "used": used,
                "limit": limit,
                "percent": round(100 * used / limit) if limit else 100,
            }
        )
    return rows


@login_required
def account(request):
    if request.GET.get("paiement") == "ok":
        messages.success(request, "Paiement reçu : votre formule s'active dans quelques instants.")
    current = services.current_subscription(request.user)
    plan = services.plan_of(request.user)
    subscriptions = request.user.subscriptions.select_related("plan")
    context = {
        "current": current,
        "plan": plan,
        "usage": _usage(request.user, plan),
        "pending": subscriptions.filter(status=Subscription.Status.PENDING),
        "history": subscriptions.exclude(status=Subscription.Status.PENDING)[:12],
        "upcoming": subscriptions.filter(
            status=Subscription.Status.ACTIVE, starts_on__gt=timezone.localdate()
        ),
        "renew_soon": current and current.days_left is not None and current.days_left <= 15,
    }
    return render(request, "billing/account.html", context)


@login_required
@require_POST
def portal(request):
    subscription = request.user.subscriptions.exclude(stripe_customer="").first()
    if subscription is None:
        raise Http404
    try:
        return redirect(stripe_gateway.portal_url(subscription, request))
    except stripe_gateway.StripeError as exc:
        messages.error(request, str(exc))
        return redirect("billing:account")


@csrf_exempt
@require_POST
def webhook(request):
    if not stripe_gateway.configured():
        raise Http404
    try:
        stripe_gateway.handle(request.body, request.headers.get("Stripe-Signature", ""))
    except ValueError:
        return HttpResponseBadRequest("invalid")
    return HttpResponse("ok")


def costs(request):
    return render(
        request,
        "billing/costs.html",
        {"costs": services.monthly_costs(), "month": timezone.localdate()},
    )
