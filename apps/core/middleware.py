from .views import health


class HealthCheckMiddleware:
    """Answer /health/ before host validation and HTTPS redirects, for container probes."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path == "/health/":
            return health(request)
        return self.get_response(request)
