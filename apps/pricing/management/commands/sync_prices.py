from django.core.management.base import BaseCommand

from apps.integrations.http import ServiceError
from apps.pricing.sync import sync_ingredient
from apps.recipes import metrics
from apps.recipes.models import Ingredient


class Command(BaseCommand):
    help = "Importe les prix récents depuis Open Prices puis recalcule les recettes."

    def add_arguments(self, parser):
        parser.add_argument(
            "slugs", nargs="*", help="Ingrédients à synchroniser (tous par défaut)."
        )
        parser.add_argument("--days", type=int, help="Profondeur d'historique en jours.")
        parser.add_argument("--pages", type=int, default=3, help="Pages de 100 prix par requête.")
        parser.add_argument("--skip-metrics", action="store_true")

    def handle(self, *args, slugs, days, pages, skip_metrics, **options):
        ingredients = Ingredient.objects.exclude(off_category="")
        if slugs:
            ingredients = ingredients.filter(slug__in=slugs)
        total = 0
        for ingredient in ingredients:
            try:
                created = sync_ingredient(ingredient, days=days, max_pages=pages)
            except ServiceError as exc:
                self.stderr.write(f"{ingredient.slug}: {exc}")
                continue
            total += created
            self.stdout.write(f"{ingredient.name}: {created} nouveau(x) prix")
        if not skip_metrics:
            metrics.refresh_all()
        self.stdout.write(self.style.SUCCESS(f"{total} nouveaux prix importés."))
