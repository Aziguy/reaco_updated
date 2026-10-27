"""Admin dashboard and Unfold callbacks."""

import json
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Max, Sum
from django.db.models.functions import TruncDate
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.utils import formats, timezone

from apps.assistant.models import Feature, Usage
from apps.assistant.services import spend_summary
from apps.pantry.models import PantryItem
from apps.pricing.models import PriceObservation
from apps.recipes.models import Recipe

DAYS = 14


def environment_callback(request):
    return ["Développement", "warning"] if settings.DEBUG else ["Production", "success"]


def _assistant_chart() -> str:
    start = timezone.localdate() - timedelta(days=DAYS - 1)
    rows = (
        Usage.objects.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day", "feature")
        .annotate(calls=Count("id"))
    )
    counts = {(row["day"], row["feature"]): row["calls"] for row in rows}
    days = [start + timedelta(days=offset) for offset in range(DAYS)]
    palette = ["#1a7e4f", "#4bb87f", "#f97316", "#80d2a5"]
    return json.dumps(
        {
            "labels": [formats.date_format(day, "j M") for day in days],
            "datasets": [
                {
                    "label": feature.label,
                    "data": [counts.get((day, feature.value), 0) for day in days],
                    "backgroundColor": color,
                }
                for feature, color in zip(Feature, palette, strict=True)
            ],
        }
    )


def dashboard_callback(request, context):
    month = timezone.localdate().replace(day=1)
    user_model = get_user_model()
    recipes = Recipe.objects.all()
    to_review = recipes.filter(is_ai_generated=True, review_requested=True, is_published=False)
    review_url = reverse("admin:recipes_recipe_changelist") + "?review_requested__exact=1"
    prices = PriceObservation.objects.aggregate(total=Count("id"), last=Max("observed_on"))
    last_price = formats.date_format(prices["last"], "j F Y") if prices["last"] else "aucun"
    new_users = user_model.objects.filter(date_joined__date__gte=month).count()
    wasted = PantryItem.objects.filter(status=PantryItem.Status.WASTED, closed_on__gte=month)
    consumed = PantryItem.objects.filter(status=PantryItem.Status.CONSUMED, closed_on__gte=month)
    saved_value = consumed.aggregate(total=Sum("estimated_value"))["total"] or 0
    usage = Usage.objects.filter(created_at__date__gte=month)
    failed = usage.filter(ok=False).count()

    saved_count, wasted_count = consumed.count(), wasted.count()
    context.update(
        {
            "title": "Tableau de bord",
            **spend_summary(),
            "kpis": [
                {
                    "title": "Recettes publiées",
                    "value": recipes.filter(is_published=True).count(),
                    "footer": f"{to_review.count()} création(s) de l'assistant à relire",
                    "url": review_url,
                },
                {
                    "title": "Utilisateurs",
                    "value": user_model.objects.count(),
                    "footer": f"+{new_users} ce mois-ci",
                    "url": reverse(f"admin:accounts_{user_model._meta.model_name}_changelist"),
                },
                {
                    "title": "Relevés de prix",
                    "value": formats.number_format(prices["total"], force_grouping=True),
                    "footer": f"Dernier relevé : {last_price}",
                    "url": reverse("admin:pricing_priceobservation_changelist"),
                },
                {
                    "title": "Anti-gaspi ce mois-ci",
                    "value": f"{saved_count} sauvé{pluralize(saved_count)}",
                    "footer": f"{wasted_count} jeté{pluralize(wasted_count)}, "
                    f"{formats.number_format(saved_value, 2)} € préservés",
                    "url": reverse("admin:pantry_pantryitem_changelist"),
                },
            ],
            "assistant_calls": usage.count(),
            "assistant_failed": failed,
            "assistant_chart": _assistant_chart(),
            "review_table": {
                "headers": ["Recette", "Auteur", "Coût / portion", "Créée le"],
                "rows": [
                    [
                        recipe.title,
                        recipe.author.email if recipe.author else "",
                        f"{formats.number_format(recipe.cost_per_serving, 2)} €"
                        if recipe.cost_per_serving
                        else "n.c.",
                        formats.date_format(recipe.created_at, "j M Y"),
                    ]
                    for recipe in to_review.select_related("author").order_by("-created_at")[:5]
                ],
            },
            "review_url": review_url,
            "recent_calls": {
                "headers": ["Date", "Fonctionnalité", "Modèle", "Coût"],
                "rows": [
                    [
                        formats.date_format(timezone.localtime(call.created_at), "d/m H:i"),
                        call.get_feature_display() + ("" if call.ok else " (échec)"),
                        call.model.label.removeprefix("Claude ") if call.model else "",
                        f"{formats.number_format(call.cost, 4)} $",
                    ]
                    for call in Usage.objects.select_related("model")[:6]
                ],
            },
        }
    )
    return context
