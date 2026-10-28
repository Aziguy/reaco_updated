"""Card payments with Stripe Checkout, off until enabled in the admin and configured."""

import logging
from datetime import UTC, datetime

import stripe
from django.conf import settings
from django.urls import reverse

from . import services
from .models import PaymentSettings, Subscription

logger = logging.getLogger(__name__)


class StripeError(Exception):
    pass


def configured() -> bool:
    return bool(settings.STRIPE["SECRET_KEY"] and settings.STRIPE["WEBHOOK_SECRET"])


def enabled(payment: PaymentSettings | None = None) -> bool:
    return configured() and (payment or PaymentSettings.load()).stripe_enabled


def _client() -> stripe.StripeClient:
    return stripe.StripeClient(settings.STRIPE["SECRET_KEY"])


def checkout_url(subscription: Subscription, request) -> str:
    price = subscription.plan.stripe_price(subscription.period)
    if not enabled() or not price:
        raise StripeError("Le paiement par carte n'est pas disponible pour cette formule.")
    reference = {"subscription": str(subscription.pk)}
    params = {
        "mode": "subscription",
        "line_items": [{"price": price, "quantity": 1}],
        "client_reference_id": str(subscription.pk),
        "metadata": reference,
        "subscription_data": {"metadata": reference},
        "success_url": request.build_absolute_uri(reverse("billing:account")) + "?paiement=ok",
        "cancel_url": request.build_absolute_uri(reverse("billing:pricing")),
    }
    if subscription.stripe_customer:
        params["customer"] = subscription.stripe_customer
    else:
        params["customer_email"] = subscription.user.email
    try:
        session = _client().v1.checkout.sessions.create(params=params)
    except stripe.StripeError as exc:
        logger.warning("Stripe checkout failed: %s", exc)
        raise StripeError("Le paiement par carte ne répond pas. Réessayez plus tard.") from exc
    return session.url


def portal_url(subscription: Subscription, request) -> str:
    if not enabled() or not subscription.stripe_customer:
        raise StripeError("Gestion par carte indisponible.")
    params = {
        "customer": subscription.stripe_customer,
        "return_url": request.build_absolute_uri(reverse("billing:account")),
    }
    try:
        return _client().v1.billing_portal.sessions.create(params=params).url
    except stripe.StripeError as exc:
        raise StripeError("L'espace de gestion Stripe ne répond pas.") from exc


def _period_end(invoice: dict):
    lines = (invoice.get("lines") or {}).get("data") or []
    end = max((line.get("period", {}).get("end") or 0 for line in lines), default=0)
    return datetime.fromtimestamp(end, UTC).date() if end else None


def _invoice_subscription(invoice: dict) -> str:
    """The subscription id, at the top level in older API versions, under parent in newer ones."""
    legacy = invoice.get("subscription")
    if legacy:
        return legacy if isinstance(legacy, str) else legacy.get("id", "")
    details = (invoice.get("parent") or {}).get("subscription_details") or {}
    return details.get("subscription") or ""


def handle(payload: bytes, signature: str) -> str:
    """Apply a signed webhook event and return its type. Raises ValueError if invalid."""
    try:
        event = _client().construct_event(payload, signature, settings.STRIPE["WEBHOOK_SECRET"])
    except (ValueError, stripe.SignatureVerificationError) as exc:
        raise ValueError("Signature Stripe invalide.") from exc
    data = event.to_dict()
    kind, obj = data["type"], data["data"]["object"]
    if kind == "checkout.session.completed":
        pk = (obj.get("metadata") or {}).get("subscription") or obj.get("client_reference_id")
        subscription = Subscription.objects.filter(pk=pk).first() if pk else None
        if subscription:
            subscription.stripe_customer = obj.get("customer") or ""
            subscription.stripe_subscription = obj.get("subscription") or ""
            subscription.save(update_fields=["stripe_customer", "stripe_subscription"])
            services.activate(subscription)
    elif kind == "invoice.paid":
        stripe_id = _invoice_subscription(obj)
        subscription = Subscription.objects.filter(stripe_subscription=stripe_id).first()
        ends_on = _period_end(obj)
        if stripe_id and subscription and ends_on:
            services.activate(subscription, ends_on=ends_on)
    elif kind == "customer.subscription.deleted":
        for subscription in Subscription.objects.filter(stripe_subscription=obj.get("id") or "-"):
            services.cancel(subscription)
    return kind
