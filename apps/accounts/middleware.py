from allauth.mfa.utils import is_mfa_enabled
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode

from . import devices

SESSION_KEY = "device_linked"


class DeviceMiddleware:
    """Put a signed token on the browser of signed-in users and link it to the account."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response
        token = request.get_signed_cookie(devices.COOKIE, default=None, salt=devices.SALT)
        if token is None:
            token = devices.new_token()
            response.set_signed_cookie(
                devices.COOKIE,
                token,
                salt=devices.SALT,
                max_age=devices.MAX_AGE,
                secure=settings.SESSION_COOKIE_SECURE,
                httponly=True,
                samesite="Lax",
            )
        token_digest = devices.digest(token)
        if request.session.get(SESSION_KEY) != token_digest:
            devices.link(user, token_digest, signed_up=getattr(request, "device_signup", False))
            request.session[SESSION_KEY] = token_digest
        return response


class StaffMFAMiddleware:
    """Staff must turn on two-factor authentication before using the admin."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.prefix = f"/{settings.ADMIN_URL}"

    def __call__(self, request):
        user = request.user
        if (
            settings.MFA_REQUIRED_FOR_STAFF
            and request.path.startswith(self.prefix)
            and user.is_authenticated
            and user.is_staff
            and not is_mfa_enabled(user)
        ):
            messages.warning(
                request,
                "Activez la double authentification pour accéder à l'administration.",
            )
            return redirect(f"{reverse('mfa_index')}?{urlencode({'next': request.path})}")
        return self.get_response(request)
