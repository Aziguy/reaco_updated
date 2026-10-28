from datetime import date, timedelta
from decimal import Decimal
from unittest import mock

import pytest
from django.core import mail
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from apps.assistant.models import Feature, Mode
from apps.assistant.services import Caller, Unavailable, availability, quota
from apps.billing import services, stripe_gateway
from apps.billing.models import Expense, PaymentSettings, Plan, Subscription, add_period

pytestmark = pytest.mark.django_db


@pytest.fixture
def plans(db):
    call_command("setup_billing")
    return {plan.slug: plan for plan in Plan.objects.all()}


@pytest.fixture
def payment(db):
    settings = PaymentSettings.load()
    settings.transfer_enabled = True
    settings.account_holder = "Association Comégusto"
    settings.iban = "FR7630006000011234567890189"
    settings.wero_enabled = True
    settings.wero_handle = "06 12 34 56 78"
    settings.save()
    return settings


def test_add_period_covers_whole_months():
    assert add_period(date(2026, 1, 15), "month") == date(2026, 2, 14)
    assert add_period(date(2026, 1, 31), "month") == date(2026, 2, 27)
    assert add_period(date(2026, 12, 1), "year") == date(2027, 11, 30)


def test_setup_billing_is_idempotent(plans):
    call_command("setup_billing")
    assert Plan.objects.count() == 3 and plans["gratuit"].is_default
    assert plans["plus"].daily_quota(Feature.RECIPE) == 8
    assert plans["plus"].ordered_quotas[0].feature == Feature.SEARCH


def test_pricing_page(client, plans, payment):
    page = client.get(reverse("billing:pricing")).content.decode()
    assert "2,99 €" in page and "24,99 €" in page and "39,99 €" in page
    assert "Virement bancaire" in page and "Wero" in page and "Carte bancaire" not in page


def test_pricing_without_payment_method(client, plans):
    assert "Bientôt disponible" in client.get(reverse("billing:pricing")).content.decode()


def test_transfer_flow(auth_client, user, plans, payment, admin_client):
    url = reverse("billing:checkout", args=["plus"])
    response = auth_client.post(url, {"period": "year", "method": "transfer"})
    subscription = Subscription.objects.get(user=user)
    assert response.url == subscription.get_absolute_url()
    assert subscription.amount == Decimal("24.99") and subscription.status == "pending"
    assert auth_client.post(url, {"period": "year", "method": "transfer"}).url == response.url

    page = auth_client.get(response.url).content.decode()
    assert "FR76 3000 6000 0112 3456 7890 189" in page and subscription.reference in page

    auth_client.post(reverse("billing:declare", args=[subscription.reference]))
    subscription.refresh_from_db()
    assert subscription.declared_at and subscription.reference in mail.outbox[-1].subject

    admin_client.post(
        reverse("admin:billing_subscription_changelist"),
        {"action": "confirm_payment", "_selected_action": [subscription.pk]},
    )
    subscription.refresh_from_db()
    assert subscription.is_current and subscription.ends_on == add_period(
        timezone.localdate(), "year"
    )
    assert "Plus" in mail.outbox[-1].subject and mail.outbox[-1].to == [user.email]
    assert services.plan_of(user) == plans["plus"]


def test_renewal_starts_after_current_period(user, plans):
    today = timezone.localdate()
    Subscription.objects.create(
        user=user, plan=plans["plus"], method="wero", amount=Decimal("2.99"), status="active",
        starts_on=today, ends_on=today + timedelta(days=10),
    )  # fmt: skip
    renewal = services.start(user, plans["plus"], "month", "wero")
    services.activate(renewal)
    assert renewal.starts_on == today + timedelta(days=11)


def test_other_users_cannot_see_payment(client, other_user, user, plans, payment):
    subscription = services.start(user, plans["plus"], "month", "transfer")
    client.force_login(other_user)
    assert client.get(subscription.get_absolute_url()).status_code == 404


def test_withdraw_pending_request(auth_client, user, plans, payment):
    subscription = services.start(user, plans["famille"], "month", "wero")
    auth_client.post(reverse("billing:withdraw", args=[subscription.reference]))
    subscription.refresh_from_db()
    assert subscription.status == "canceled"


def test_plan_quotas_drive_the_assistant(user, plans, fake_ai):
    caller = Caller(user, "1.2.3.4")
    route = availability(Feature.RECIPE, Mode.FAST, caller)
    assert quota(route, caller) == 2
    with pytest.raises(Unavailable) as error:
        availability(Feature.RECIPE, Mode.DEEP, caller)
    assert error.value.reason == "plan" and "Famille" in error.value.message
    Subscription.objects.create(
        user=user, plan=plans["famille"], method="wero", amount=Decimal("4.99"), status="active",
        starts_on=timezone.localdate(), ends_on=timezone.localdate(),
    )  # fmt: skip
    assert availability(Feature.RECIPE, Mode.DEEP, caller).mode == Mode.DEEP
    assert quota(route, caller) == 20


def test_account_page(auth_client, user, plans, fake_ai):
    page = auth_client.get(reverse("billing:account")).content.decode()
    assert "Gratuit" in page and "0</strong> / 10" in page


def test_costs_page(client, user, plans):
    Expense.objects.create(label="Hébergement", category="hosting", monthly_amount=Decimal(10))
    Subscription.objects.create(
        user=user, plan=plans["plus"], method="wero", amount=Decimal("24.00"), period="year",
        status="active", starts_on=timezone.localdate(), ends_on=timezone.localdate(),
    )  # fmt: skip
    costs = services.monthly_costs()
    assert costs.revenue == Decimal("2.00") and costs.coverage == 20
    page = client.get(reverse("billing:costs")).content.decode()
    assert "20 % des frais couverts" in page and "Hébergement" in page


def test_stripe_is_off_by_default(auth_client, plans, payment, client):
    assert not stripe_gateway.enabled()
    response = auth_client.post(
        reverse("billing:checkout", args=["plus"]), {"period": "month", "method": "stripe"}
    )
    assert response.status_code == 200 and not Subscription.objects.exists()
    assert client.post(reverse("billing:webhook")).status_code == 404


@pytest.fixture
def stripe_on(settings, payment):
    settings.STRIPE = {"SECRET_KEY": "sk_test_x", "WEBHOOK_SECRET": "whsec_x"}
    payment.stripe_enabled = True
    payment.save()
    return payment


def test_stripe_checkout_redirects(auth_client, user, plans, stripe_on):
    Plan.objects.filter(slug="plus").update(stripe_monthly_price="price_123")
    session = mock.Mock(url="https://checkout.stripe.com/c/pay/x")
    with mock.patch("stripe.StripeClient") as client_class:
        client_class.return_value.v1.checkout.sessions.create.return_value = session
        response = auth_client.post(
            reverse("billing:checkout", args=["plus"]), {"period": "month", "method": "stripe"}
        )
    params = client_class.return_value.v1.checkout.sessions.create.call_args.kwargs["params"]
    assert response.url == session.url and params["line_items"][0]["price"] == "price_123"
    assert params["customer_email"] == user.email


def _event(kind, obj):
    event = mock.Mock()
    event.to_dict.return_value = {"type": kind, "data": {"object": obj}}
    return event


def test_stripe_webhook_lifecycle(client, user, plans, stripe_on):
    subscription = services.start(user, plans["plus"], "month", "stripe")
    url = reverse("billing:webhook")
    end = int((timezone.now() + timedelta(days=40)).timestamp())
    events = [
        _event(
            "checkout.session.completed",
            {"metadata": {"subscription": str(subscription.pk)}, "customer": "cus_1",
             "subscription": "sub_1"},
        ),
        _event(
            "invoice.paid",
            {"parent": {"subscription_details": {"subscription": "sub_1"}},
             "lines": {"data": [{"period": {"end": end}}]}},
        ),
        _event("customer.subscription.deleted", {"id": "sub_1"}),
    ]  # fmt: skip
    with mock.patch("stripe.StripeClient") as client_class:
        client_class.return_value.construct_event.side_effect = events
        assert client.post(url, b"{}", content_type="application/json").status_code == 200
        subscription.refresh_from_db()
        assert subscription.is_current and subscription.stripe_customer == "cus_1"
        client.post(url, b"{}", content_type="application/json")
        subscription.refresh_from_db()
        assert subscription.ends_on == timezone.localdate() + timedelta(days=40)
        client.post(url, b"{}", content_type="application/json")
    subscription.refresh_from_db()
    assert subscription.status == "canceled"


def test_stripe_webhook_rejects_bad_signature(client, stripe_on):
    with mock.patch("stripe.StripeClient") as client_class:
        client_class.return_value.construct_event.side_effect = ValueError("bad")
        response = client.post(reverse("billing:webhook"), b"{}", content_type="application/json")
    assert response.status_code == 400


def test_admin_billing_pages(admin_client, plans, payment):
    assert admin_client.get(reverse("admin:billing_paymentsettings_changelist")).status_code == 302
    for name in ("subscription", "plan", "expense"):
        assert admin_client.get(reverse(f"admin:billing_{name}_changelist")).status_code == 200
    plus = plans["plus"]
    assert admin_client.get(reverse("admin:billing_plan_change", args=[plus.pk])).status_code == 200
