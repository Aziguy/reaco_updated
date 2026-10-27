"""Third-party admins re-registered with the Unfold theme."""

from allauth.account.admin import EmailAddressAdmin
from allauth.account.models import EmailAddress
from allauth.socialaccount.admin import SocialAccountAdmin, SocialAppAdmin, SocialTokenAdmin
from allauth.socialaccount.models import SocialAccount, SocialApp, SocialToken
from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin
from django.contrib.auth.models import Group
from rest_framework.authtoken.admin import TokenAdmin
from rest_framework.authtoken.models import TokenProxy
from unfold.admin import ModelAdmin

for model, base in [
    (Group, GroupAdmin),
    (EmailAddress, EmailAddressAdmin),
    (SocialApp, SocialAppAdmin),
    (SocialAccount, SocialAccountAdmin),
    (SocialToken, SocialTokenAdmin),
    (TokenProxy, TokenAdmin),
]:
    if admin.site.is_registered(model):
        admin.site.unregister(model)
    admin.site.register(model, type(base.__name__, (base, ModelAdmin), {}))
