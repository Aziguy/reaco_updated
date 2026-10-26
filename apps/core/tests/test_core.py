import pytest
from django.core import mail
from django.urls import reverse

CONTACT = {"name": "Ana", "email": "ana@example.com", "subject": "Bonjour", "message": "Merci !"}


@pytest.mark.django_db
class TestPages:
    @pytest.mark.parametrize("name", ["home", "season", "about", "contact"])
    def test_public_pages_survive_open_data_outage(self, client, recipe, name):
        assert client.get(reverse(f"core:{name}")).status_code == 200

    def test_dashboard(self, auth_client):
        assert auth_client.get(reverse("core:dashboard")).status_code == 200

    def test_health(self, client):
        assert client.get(reverse("core:health")).json() == {"status": "ok"}

    def test_security_headers(self, client):
        response = client.get(reverse("core:home"))
        assert "default-src 'self'" in response["Content-Security-Policy"]
        assert response["X-Frame-Options"] == "DENY"


@pytest.mark.django_db
class TestContact:
    def test_sends_mail(self, client):
        client.post(reverse("core:contact"), CONTACT)
        assert len(mail.outbox) == 1

    def test_honeypot(self, client):
        client.post(reverse("core:contact"), {**CONTACT, "website": "spam.example"})
        assert mail.outbox == []

    def test_rate_limit(self, client):
        for _ in range(5):
            client.post(reverse("core:contact"), CONTACT)
        assert len(mail.outbox) == 3
