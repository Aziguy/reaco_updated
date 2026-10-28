import time

import pytest
from allauth.account.models import EmailAddress
from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value
from allauth.mfa.utils import decrypt
from django.core.management import call_command
from django.urls import reverse

from apps.accounts import devices
from apps.accounts.emails import canonical, is_disposable
from apps.accounts.models import DeviceLink, User
from apps.assistant.models import Feature, Mode, Usage
from apps.assistant.services import Caller, Unavailable, availability, used_today
from apps.billing import services as billing
from apps.conftest import with_mfa

pytestmark = pytest.mark.django_db
SIGNUP = {"password1": "Un-mot-de-passe-1", "password2": "Un-mot-de-passe-1"}


def signup(client, email):
    return client.post(reverse("account_signup"), {"email": email, **SIGNUP})


@pytest.mark.parametrize(
    ("email", "expected"),
    [
        ("Jean.Dupont+promo@GMail.com", "jeandupont@gmail.com"),
        ("jean.dupont@googlemail.com", "jeandupont@gmail.com"),
        ("jean.dupont+x@laposte.net", "jean.dupont@laposte.net"),
    ],
)
def test_canonical_email(email, expected):
    assert canonical(email) == expected


def test_disposable_domains(settings):
    settings.BLOCKED_EMAIL_DOMAINS = ["jetable.example"]
    assert is_disposable("a@mailinator.com")
    assert is_disposable("a@inbox.mailinator.com")
    assert is_disposable("a@jetable.example")
    assert not is_disposable("a@gmail.com")


def test_signup_refuses_disposable_and_alias_addresses(client):
    User.objects.create_user(email="jean.dupont@gmail.com", password="x")
    assert "temporaires" in signup(client, "a@yopmail.com").content.decode()
    assert "existe déjà" in signup(client, "Jean.Dupont+2@googlemail.com").content.decode()
    assert User.objects.count() == 1


def test_signups_per_ip_are_limited(client, settings):
    settings.SIGNUP_LIMIT_PER_IP = 2
    for n in range(2):
        assert signup(client, f"user{n}@example.com").status_code == 302
        client.logout()
    assert "Trop de comptes" in signup(client, "user3@example.com").content.decode()
    assert User.objects.count() == 2


def test_device_token_links_accounts(client):
    assert signup(client, "first@example.com").status_code == 302
    client.get(reverse("core:home"))
    token = client.cookies[devices.COOKIE]
    assert token["httponly"]
    first = User.objects.get(email="first@example.com")
    link = DeviceLink.objects.get(user=first)
    assert link.signed_up
    assert link.device.digest != token.value

    client.logout()
    client.cookies[devices.COOKIE] = token.value
    second = User.objects.create_user(email="second@example.com", password="x")
    client.force_login(second)
    client.get(reverse("core:home"))
    assert list(devices.linked_users(second)) == [first]


def test_anonymous_visitors_get_no_device_cookie(client):
    client.get(reverse("core:home"))
    assert devices.COOKIE not in client.cookies


def share_device(*users):
    for user in users:
        devices.link(user, devices.digest("same-browser"))


def test_free_accounts_of_a_device_share_the_quota(ai_config, user, other_user):
    share_device(user, other_user)
    Usage.objects.create(user=user, feature=Feature.SEARCH, mode=Mode.FAST)
    route = availability(Feature.SEARCH, Mode.FAST, Caller(other_user, ""))
    assert used_today(route, Caller(other_user, "")) == 1


def test_subscribers_and_staff_keep_their_own_quota(ai_config, user, other_user, admin_user):
    call_command("setup_billing")
    share_device(user, other_user, admin_user)
    Usage.objects.create(user=user, feature=Feature.SEARCH, mode=Mode.FAST)
    Usage.objects.create(user=admin_user, feature=Feature.SEARCH, mode=Mode.FAST)
    subscription = billing.start(other_user, billing.plans().get(slug="plus"), "month", "transfer")
    billing.activate(subscription)
    route = availability(Feature.SEARCH, Mode.FAST, Caller(other_user, ""))
    assert used_today(route, Caller(other_user, "")) == 0
    assert used_today(route, Caller(admin_user, "")) == 1
    assert used_today(route, Caller(user, "")) == 1


def test_assistant_needs_a_verified_email(ai_config, user):
    EmailAddress.objects.create(user=user, email=user.email, primary=True, verified=False)
    with pytest.raises(Unavailable) as exc:
        availability(Feature.SEARCH, Mode.FAST, Caller(user, ""))
    assert exc.value.reason == "verify"
    EmailAddress.objects.filter(user=user).update(verified=True)
    availability(Feature.SEARCH, Mode.FAST, Caller(user, ""))


def test_admin_login_goes_through_the_site_login(client):
    response = client.get(reverse("admin:login"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("account_login"))


def test_staff_must_turn_on_two_factor(client, settings):
    staff = User.objects.create_superuser(email="staff@example.com", password="x")
    client.force_login(staff)
    response = client.get(reverse("admin:index"))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("mfa_index"))
    with_mfa(staff)
    assert client.get(reverse("admin:index")).status_code == 200


def test_staff_rule_can_be_turned_off(client, settings):
    settings.MFA_REQUIRED_FOR_STAFF = False
    client.force_login(User.objects.create_superuser(email="staff@example.com", password="x"))
    assert client.get(reverse("admin:index")).status_code == 200


def test_login_asks_for_the_authenticator_code(client, user):
    with_mfa(user)
    secret = user.authenticator_set.get().wrap().instance.data["secret"]
    response = client.post(
        reverse("account_login"), {"login": user.email, "password": "secret-pass-123"}
    )
    assert response["Location"] == reverse("mfa_authenticate")
    page = client.get(reverse("mfa_authenticate")).content.decode()
    assert "Double authentification" in page
    assert "_auth_user_id" not in client.session

    code = format_hotp_value(hotp_value(decrypt(secret), int(time.time()) // 30))
    response = client.post(reverse("mfa_authenticate"), {"code": code})
    assert response["Location"] == reverse("mfa_trust")
    client.post(reverse("mfa_trust"), {"action": "skip"})
    assert client.session["_auth_user_id"] == str(user.pk)


def test_security_pages_render(auth_client, user):
    page = auth_client.get(reverse("mfa_index")).content.decode()
    assert "Application d'authentification" in page
    assert "Clés d'accès" in page
    assert "Sécurité du compte" in auth_client.get(reverse("accounts:profile")).content.decode()
    with_mfa(user)
    page = auth_client.get(reverse("mfa_index")).content.decode()
    assert "Double authentification active" in page


def test_login_page_offers_passkeys(client):
    page = client.get(reverse("account_login")).content.decode()
    assert 'id="passkey_login"' in page
    assert "webauthn.js" in page


def test_admin_shows_two_factor_and_linked_accounts(admin_client, user, other_user):
    share_device(user, other_user)
    with_mfa(user)
    changelist = reverse("admin:accounts_user_changelist")
    page = admin_client.get(f"{changelist}?partage=1").content.decode()
    assert user.email in page and other_user.email in page
    assert other_user.email not in admin_client.get(f"{changelist}?mfa=1").content.decode()
    change = admin_client.get(reverse("admin:accounts_user_change", args=[user.pk]))
    assert other_user.email in change.content.decode()

    admin_client.post(changelist, {"action": "reset_mfa", "_selected_action": [user.pk]})
    assert not user.authenticator_set.exists()
