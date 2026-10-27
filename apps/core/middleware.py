from csp.constants import UNSAFE_EVAL, UNSAFE_INLINE
from csp.middleware import CSPMiddleware as BaseCSPMiddleware
from django.conf import settings

from .views import health

# The admin theme (Unfold) relies on Alpine.js expressions and inline style attributes.
ADMIN_CSP = {"script-src": [UNSAFE_EVAL], "style-src": [UNSAFE_INLINE]}


class HealthCheckMiddleware:
    """Answer /health/ before host validation and HTTPS redirects, for container probes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return health(request)
        return self.get_response(request)


class CSPMiddleware(BaseCSPMiddleware):
    """Strict CSP everywhere, relaxed only for the admin."""

    def get_policy_parts(self, request, response, report_only=False):
        parts = super().get_policy_parts(request, response, report_only)
        if request.path.startswith(f"/{settings.ADMIN_URL}"):
            parts.update = {**ADMIN_CSP, **(parts.update or {})}
        return parts
