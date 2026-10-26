from django.conf import settings


def site(request):
    return {
        "SITE_NAME": settings.SITE_NAME,
        "CONTACT_EMAIL": settings.CONTACT_EMAIL,
        "GOOGLE_LOGIN": bool(settings.GOOGLE_CLIENT_ID),
    }
