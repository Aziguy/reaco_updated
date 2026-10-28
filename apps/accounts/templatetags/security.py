from allauth.mfa.models import Authenticator
from django import template

register = template.Library()


@register.filter
def mfa_types(user) -> set[str]:
    if not user or not user.pk:
        return set()
    return set(Authenticator.objects.filter(user=user).values_list("type", flat=True))


@register.filter
def mfa_blocked(user) -> bool:
    """allauth refuses a second factor while an address is unverified."""
    from allauth.account.models import EmailAddress
    from allauth.mfa import app_settings

    if app_settings.ALLOW_UNVERIFIED_EMAIL:
        return False
    return EmailAddress.objects.filter(user=user, verified=False).exists()
