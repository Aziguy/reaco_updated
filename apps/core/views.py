import logging
from collections import defaultdict

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.mail import send_mail
from django.db import connection
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from apps.integrations.http import ServiceError
from apps.integrations.impactco2 import seasonal_produce
from apps.pantry.models import PantryItem
from apps.pantry.services import stats_for, suggest_recipes
from apps.pricing.models import PriceObservation, Store
from apps.recipes.models import Ingredient, Recipe

from .forms import ContactForm
from .ratelimit import allow, client_ip

logger = logging.getLogger(__name__)

MONTHS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]  # fmt: skip


def produce_of(month: int):
    try:
        return seasonal_produce(month)
    except ServiceError:
        return []


def home(request):
    recipes = Recipe.objects.published().prefetch_related("diets")
    stats = cache.get_or_set(
        "home:stats",
        lambda: {
            "recipes": Recipe.objects.published().count(),
            "prices": PriceObservation.objects.count(),
            "stores": Store.objects.count(),
        },
        600,
    )
    month = timezone.localdate().month
    context = {
        "featured": recipes.filter(is_featured=True)[:6],
        "cheapest": recipes.filter(cost_per_serving__isnull=False).order_by("cost_per_serving")[:4],
        "produce": produce_of(month)[:12],
        "month_name": MONTHS[month - 1],
        "stats": stats,
    }
    return render(request, "core/home.html", context)


@login_required
def dashboard(request):
    user = request.user
    context = {
        "stats": stats_for(user),
        "expiring": PantryItem.objects.filter(user=user).expiring()[:6],
        "suggestions": suggest_recipes(user, limit=3),
        "lists": user.shopping_lists.filter(is_archived=False)[:4],
        "favorites": Recipe.objects.filter(favorites__user=user).order_by("-favorites__created_at")[
            :4
        ],
    }
    return render(request, "core/dashboard.html", context)


def season(request):
    try:
        month = min(max(int(request.GET.get("mois", "")), 1), 12)
    except ValueError:
        month = timezone.localdate().month
    produce = produce_of(month)
    groups = defaultdict(list)
    for item in produce:
        groups[item.category or "autres"].append(item)
    slugs = {item.slug for item in produce}
    ingredients = Ingredient.objects.filter(impactco2_slug__in=slugs, is_staple=False)
    recipes = (
        Recipe.objects.published().filter(items__ingredient__in=ingredients).distinct()[:6]
        if slugs
        else []
    )
    context = {
        "month": month,
        "month_name": MONTHS[month - 1],
        "months": list(enumerate(MONTHS, start=1)),
        "groups": dict(sorted(groups.items())),
        "recipes": recipes,
        "unavailable": not produce,
    }
    return render(request, "core/season.html", context)


def about(request):
    return render(request, "core/about.html")


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        if not allow(f"contact:{client_ip(request)}", limit=3, window=3600):
            messages.error(request, "Trop de messages envoyés. Réessayez plus tard.")
        else:
            if not form.is_spam():
                data = form.cleaned_data
                send_mail(
                    f"[{settings.SITE_NAME}] {data['subject']}",
                    f"De : {data['name']} <{data['email']}>\n\n{data['message']}",
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.CONTACT_EMAIL],
                    fail_silently=True,
                )
            messages.success(request, "Merci, votre message a bien été envoyé.")
            return redirect("core:contact")
    return render(request, "core/contact.html", {"form": form})


@never_cache
@require_GET
def health(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        logger.exception("Health check failed")
        return JsonResponse({"status": "error"}, status=503)
    return JsonResponse({"status": "ok"})
