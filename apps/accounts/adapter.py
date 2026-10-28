from allauth.account.adapter import DefaultAccountAdapter
from django import forms

from .emails import is_disposable


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        email = super().clean_email(email)
        if is_disposable(email):
            raise forms.ValidationError(
                "Les adresses email temporaires ne sont pas acceptées. "
                "Utilisez votre adresse habituelle."
            )
        return email
