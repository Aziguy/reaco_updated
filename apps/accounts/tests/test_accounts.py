import importlib

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

GEOCODING_URL = "https://data.geopf.fr/geocodage/search"


@pytest.mark.django_db
def test_create_user_requires_email():
    with pytest.raises(ValueError):
        get_user_model().objects.create_user(email="")


@pytest.mark.django_db
def test_signup_with_email(client):
    response = client.post(
        reverse("account_signup"),
        {
            "email": "new@example.com",
            "password1": "Un-mot-de-passe-1",
            "password2": "Un-mot-de-passe-1",
        },
    )
    assert response.status_code == 302
    assert get_user_model().objects.filter(email="new@example.com").exists()


@pytest.mark.django_db
class TestProfile:
    def payload(self, **extra):
        data = {"household_size": 3, "search_radius_km": 15, "postal_code": "83000"}
        data.update(extra)
        return data

    def test_postal_code_is_geocoded(self, auth_client, user, http):
        http.get(GEOCODING_URL).respond(
            json={
                "features": [
                    {
                        "geometry": {"coordinates": [5.93, 43.13]},
                        "properties": {"city": "Toulon", "postcode": "83000"},
                    }
                ]
            }
        )
        auth_client.post(reverse("accounts:profile"), self.payload())
        user.refresh_from_db()
        assert (user.city, user.latitude, user.longitude) == ("Toulon", 43.13, 5.93)
        assert user.location == (43.13, 5.93, 15)

    def test_unknown_postal_code(self, auth_client, http):
        http.get(GEOCODING_URL).respond(json={"features": []})
        response = auth_client.post(reverse("accounts:profile"), self.payload(postal_code="00000"))
        assert "Code postal introuvable" in response.content.decode()

    def test_browser_coordinates(self, auth_client, user):
        auth_client.post(
            reverse("accounts:profile"),
            self.payload(postal_code="", latitude="45.76", longitude="4.83"),
        )
        user.refresh_from_db()
        assert user.has_location


@pytest.mark.django_db
def test_delete_account(auth_client, user):
    response = auth_client.post(reverse("accounts:delete"), {"confirm": "supprimer"})
    assert response.status_code == 302
    assert not get_user_model().objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_delete_account_needs_confirmation(auth_client, user):
    auth_client.post(reverse("accounts:delete"), {"confirm": "oui"})
    assert get_user_model().objects.filter(pk=user.pk).exists()


def test_google_provider_dependencies_are_installed():
    importlib.import_module("allauth.socialaccount.providers.google.provider")
