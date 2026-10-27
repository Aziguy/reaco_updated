from pathlib import Path

import environ
from csp.constants import NONE, SELF
from django.templatetags.static import static
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env("SECRET_KEY", default="django-insecure-dev-only") if DEBUG else env("SECRET_KEY")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

SITE_NAME = "Comégusto"
ADMIN_URL = env("ADMIN_URL", default="admin/")
SERVE_MEDIA = env.bool("SERVE_MEDIA", default=True)
CONTACT_EMAIL = env("CONTACT_EMAIL", default="contact@comegusto.local")

GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "whitenoise.runserver_nostatic",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "rest_framework.authtoken",
    "drf_spectacular",
    "drf_spectacular_sidecar",
    "django_htmx",
    "csp",
    "apps.core",
    "apps.accounts",
    "apps.recipes",
    "apps.integrations",
    "apps.pricing",
    "apps.pantry",
    "apps.shopping",
    "apps.api",
    "apps.guide",
    "apps.assistant",
]
if GOOGLE_CLIENT_ID:
    INSTALLED_APPS.append("allauth.socialaccount.providers.google")

MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.core.middleware.CSPMiddleware",
    "allauth.account.middleware.AccountMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.site",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REDIS_URL = env("REDIS_URL", default="")
CACHES = {
    "default": (
        {"BACKEND": "django.core.cache.backends.redis.RedisCache", "LOCATION": REDIS_URL}
        if REDIS_URL
        else {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
    )
}

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LOGIN_URL = "account_login"
LOGIN_REDIRECT_URL = "core:dashboard"
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = env("ACCOUNT_EMAIL_VERIFICATION", default="optional")
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
ACCOUNT_SESSION_REMEMBER = None
SOCIALACCOUNT_PROVIDERS = {}
if GOOGLE_CLIENT_ID:
    SOCIALACCOUNT_PROVIDERS["google"] = {
        "APPS": [{"client_id": GOOGLE_CLIENT_ID, "secret": GOOGLE_CLIENT_SECRET, "key": ""}],
        "SCOPE": ["profile", "email"],
    }

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
LOCALE_PATHS = [BASE_DIR / "locale"]
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
MEDIA_HOSTS = []
if AWS_STORAGE_BUCKET_NAME:
    s3_endpoint = env("AWS_S3_ENDPOINT_URL", default="") or None
    s3_domain = env("AWS_S3_CUSTOM_DOMAIN", default="") or None
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "access_key": env("AWS_ACCESS_KEY_ID"),
            "secret_key": env("AWS_SECRET_ACCESS_KEY"),
            "endpoint_url": s3_endpoint,
            "region_name": env("AWS_S3_REGION_NAME", default="") or None,
            "custom_domain": s3_domain,
            "querystring_auth": not s3_domain,
            "file_overwrite": False,
            "default_acl": None,
        },
    }
    MEDIA_HOSTS = (
        [f"https://{s3_domain}"] if s3_domain else [s3_endpoint or "https://*.amazonaws.com"]
    )
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

EMAIL_CONFIG = env.email_url("EMAIL_URL", default="consolemail://")
vars().update(EMAIL_CONFIG)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=10)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default=f"Comégusto <{CONTACT_EMAIL}>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL
ADMINS = [("Admin", email) for email in env.list("ADMINS", default=[])]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=not DEBUG)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
SILENCED_SYSTEM_CHECKS = [] if SECURE_HSTS_PRELOAD else ["security.W021"]
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SESSION_COOKIE_SECURE = env.bool("SECURE_COOKIES", default=not DEBUG)
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
X_FRAME_OPTIONS = "DENY"

OFF_IMAGE_HOSTS = ["https://images.openfoodfacts.org", "https://static.openfoodfacts.org"]
CONTENT_SECURITY_POLICY = {
    "DIRECTIVES": {
        "default-src": [SELF],
        "script-src": [SELF],
        "style-src": [SELF],
        "img-src": [
            SELF,
            "data:",
            "blob:",
            *OFF_IMAGE_HOSTS,
            *MEDIA_HOSTS,
            "https://raw.githubusercontent.com",
        ],
        "connect-src": [SELF],
        "font-src": [SELF],
        "object-src": [NONE],
        "base-uri": [SELF],
        "frame-ancestors": [NONE],
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticatedOrReadOnly"],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "240/min"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Comégusto API",
    "DESCRIPTION": "Recettes, estimation de prix, garde-manger et listes de courses.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SWAGGER_UI_DIST": "SIDECAR",
    "SWAGGER_UI_FAVICON_HREF": "SIDECAR",
    "REDOC_DIST": "SIDECAR",
}

INTEGRATIONS = {
    "USER_AGENT": f"Comegusto/2.0 ({CONTACT_EMAIL})",
    "TIMEOUT": env.float("INTEGRATIONS_TIMEOUT", default=8.0),
    "RETRIES": 2,
    "BACKOFF": 0.5,
    "OPEN_FOOD_FACTS_URL": "https://world.openfoodfacts.org",
    "OPEN_PRICES_URL": "https://prices.openfoodfacts.org",
    "IMPACT_CO2_URL": "https://impactco2.fr/api/v1",
    "IMPACT_CO2_API_KEY": env("IMPACT_CO2_API_KEY", default=""),
    "GEOCODING_URL": "https://data.geopf.fr/geocodage",
}
AI = {
    "ENABLED": env.bool("AI_ENABLED", default=True),
    "MONTHLY_BUDGET_USD": env.float("AI_MONTHLY_BUDGET_USD", default=20.0),
    "TIMEOUT": env.float("AI_TIMEOUT", default=60.0),
}


def _admin_link(title, icon, model):
    app, name = model.split(".")
    return {"title": title, "icon": icon, "link": reverse_lazy(f"admin:{app}_{name}_changelist")}


UNFOLD = {
    "SITE_TITLE": "Comégusto",
    "SITE_HEADER": "Comégusto",
    "SITE_SUBHEADER": "Administration",
    "SITE_URL": "/",
    "SITE_LOGO": {
        "light": lambda request: static("img/logos/comegusto-dark.png"),
        "dark": lambda request: static("img/logos/comegusto-light.png"),
    },
    "SITE_FAVICONS": [
        {"rel": "icon", "type": "image/svg+xml", "href": lambda request: static("img/favicon.svg")}
    ],
    "SHOW_VIEW_ON_SITE": True,
    "ENVIRONMENT": "apps.core.dashboard.environment_callback",
    "DASHBOARD_CALLBACK": "apps.core.dashboard.dashboard_callback",
    "STYLES": [lambda request: static("css/admin.css")],
    "BORDER_RADIUS": "10px",
    "COLORS": {
        "base": {
            "50": "oklch(98.5% .001 106.423)",
            "100": "oklch(97% .001 106.424)",
            "200": "oklch(92.3% .003 48.717)",
            "300": "oklch(86.9% .005 56.366)",
            "400": "oklch(70.9% .01 56.259)",
            "500": "oklch(55.3% .013 58.071)",
            "600": "oklch(44.4% .011 73.639)",
            "700": "oklch(37.4% .01 67.558)",
            "800": "oklch(26.8% .007 34.298)",
            "900": "oklch(21.6% .006 56.043)",
            "950": "oklch(14.7% .004 49.25)",
        },
        "primary": {
            "50": "#effaf3",
            "100": "#d8f3e1",
            "200": "#b3e6c7",
            "300": "#80d2a5",
            "400": "#4bb87f",
            "500": "#289c63",
            "600": "#1a7e4f",
            "700": "#166541",
            "800": "#145136",
            "900": "#11432e",
            "950": "#08251a",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": [
            {
                "title": "Pilotage",
                "items": [
                    {
                        "title": "Tableau de bord",
                        "icon": "space_dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": "Catalogue",
                "collapsible": True,
                "items": [
                    _admin_link("Recettes", "restaurant_menu", "recipes.recipe"),
                    _admin_link("Ingrédients", "nutrition", "recipes.ingredient"),
                    _admin_link("Régimes", "eco", "recipes.diet"),
                ],
            },
            {
                "title": "Prix",
                "collapsible": True,
                "items": [
                    _admin_link("Relevés de prix", "sell", "pricing.priceobservation"),
                    _admin_link("Magasins", "storefront", "pricing.store"),
                ],
            },
            {
                "title": "Utilisateurs",
                "collapsible": True,
                "items": [
                    _admin_link("Utilisateurs", "person", "accounts.user"),
                    _admin_link("Garde-manger", "kitchen", "pantry.pantryitem"),
                    _admin_link("Listes de courses", "shopping_cart", "shopping.shoppinglist"),
                    _admin_link("Groupes", "group", "auth.group"),
                ],
            },
            {
                "title": "Assistant IA",
                "collapsible": True,
                "items": [
                    _admin_link("Journal des appels", "monitoring", "assistant.usage"),
                    _admin_link("Routes et quotas", "alt_route", "assistant.route"),
                    _admin_link("Modèles", "smart_toy", "assistant.aimodel"),
                    _admin_link("Fournisseurs", "hub", "assistant.provider"),
                    _admin_link("Menus", "calendar_month", "assistant.mealplan"),
                ],
            },
            {
                "title": "Connexion et API",
                "collapsible": True,
                "items": [
                    _admin_link("Adresses email", "mail", "account.emailaddress"),
                    _admin_link("Comptes sociaux", "account_circle", "socialaccount.socialaccount"),
                    _admin_link("Applications OAuth", "key", "socialaccount.socialapp"),
                    _admin_link("Jetons d'API", "token", "authtoken.tokenproxy"),
                ],
            },
        ],
    },
}

PRICING = {
    "COUNTRIES": env.list("PRICE_COUNTRIES", default=["FR"]),
    "CURRENCY": "EUR",
    "HISTORY_DAYS": env.int("PRICE_HISTORY_DAYS", default=365),
    "MIN_OBSERVATIONS": 1,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"simple": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "simple"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {"httpx": {"level": "WARNING"}, "httpx2": {"level": "WARNING"}},
}
