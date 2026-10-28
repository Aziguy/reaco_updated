import time

import pytest
from allauth.mfa.totp.internal.auth import format_hotp_value, hotp_value
from allauth.mfa.utils import decrypt
from django.urls import reverse

from apps.accounts.models import User
from apps.conftest import with_mfa

pytestmark = pytest.mark.django_db


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


def test_admin_shows_and_resets_two_factor(admin_client, user, other_user):
    with_mfa(user)
    changelist = reverse("admin:accounts_user_changelist")
    page = admin_client.get(f"{changelist}?mfa=1").content.decode()
    assert user.email in page and other_user.email not in page
    admin_client.post(changelist, {"action": "reset_mfa", "_selected_action": [user.pk]})
    assert not user.authenticator_set.exists()
