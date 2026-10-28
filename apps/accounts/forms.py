from allauth.account.forms import SignupForm as BaseSignupForm
from allauth.core import context
from django import forms
from django.conf import settings

from apps.core.ratelimit import client_ip
from apps.integrations.geocoding import geocode_city
from apps.integrations.http import ServiceError

from .emails import canonical, signups_from
from .models import User


class ProfileForm(forms.ModelForm):
    latitude = forms.FloatField(
        widget=forms.HiddenInput, required=False, min_value=-90, max_value=90
    )
    longitude = forms.FloatField(
        widget=forms.HiddenInput, required=False, min_value=-180, max_value=180
    )

    class Meta:
        model = User
        fields = [
            "first_name",
            "last_name",
            "household_size",
            "postal_code",
            "search_radius_km",
            "latitude",
            "longitude",
            "expiry_reminders",
        ]
        help_texts = {
            "postal_code": "Utilisé pour comparer les prix des magasins proches de chez vous.",
            "household_size": "Nombre de portions proposé par défaut.",
        }

    def clean(self):
        data = super().clean()
        postal_code = (data.get("postal_code") or "").strip()
        changed = "postal_code" in self.changed_data
        if postal_code and changed:
            try:
                place = geocode_city(postal_code)
            except ServiceError:
                place = None
            if place is None:
                self.add_error("postal_code", "Code postal introuvable.")
            else:
                data.update(
                    postal_code=place.postal_code,
                    latitude=place.latitude,
                    longitude=place.longitude,
                )
                self.instance.city = place.city
        elif not postal_code and not data.get("latitude"):
            data.update(latitude=None, longitude=None)
            self.instance.city = ""
        return data


class DeleteAccountForm(forms.Form):
    confirm = forms.CharField(label="Tapez SUPPRIMER pour confirmer")

    def clean_confirm(self):
        if self.cleaned_data["confirm"].strip().upper() != "SUPPRIMER":
            raise forms.ValidationError("Confirmation incorrecte.")
        return self.cleaned_data["confirm"]


class SignupForm(BaseSignupForm):
    def clean_email(self):
        email = super().clean_email()
        if User.objects.filter(email_canonical=canonical(email)).exists():
            raise forms.ValidationError(
                "Un compte existe déjà pour cette boîte mail. "
                "Connectez-vous ou réinitialisez votre mot de passe."
            )
        return email

    def clean(self):
        data = super().clean()
        limit = settings.SIGNUP_LIMIT_PER_IP
        request = context.request
        if limit and request and signups_from(client_ip(request)) >= limit:
            raise forms.ValidationError(
                "Trop de comptes ont été créés depuis cette connexion aujourd'hui. "
                "Réessayez demain."
            )
        return data
