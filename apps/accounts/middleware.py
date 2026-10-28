from allauth.mfa.utils import is_mfa_enabled
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import urlencode


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
