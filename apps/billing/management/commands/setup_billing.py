from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.assistant.models import Feature
from apps.billing.models import PaymentSettings, Plan, PlanQuota

# slug, name, tagline, monthly, yearly, deep mode, default, highlighted, features, quotas
PLANS = [
    (
        "gratuit", "Gratuit", "Pour découvrir et cuisiner malin au quotidien.", "0", "0",
        False, True, False,
        "Catalogue, prix et comparateur de magasins\nGarde-manger et listes de courses\n"
        "Assistant IA pour découvrir",
        {Feature.SEARCH: 10, Feature.RECIPE: 2, Feature.PHOTO: 2, Feature.RECEIPT: 1,
         Feature.PLANNER: 1},
    ),
    (
        "plus", "Plus", "L'assistant IA à vos côtés tous les jours.", "2.99", "24.99",
        False, False, True,
        "Tout ce qui est gratuit\nAssistant IA au quotidien\nPhotos d'ingrédients et de tickets",
        {Feature.SEARCH: 50, Feature.RECIPE: 8, Feature.PHOTO: 8, Feature.RECEIPT: 8,
         Feature.PLANNER: 3},
    ),
    (
        "famille", "Famille", "Pour les grandes tablées et les plus gourmands.", "4.99", "39.99",
        True, False, False,
        "Tout ce que contient Plus\nMode Approfondi, plus fin sur les demandes complexes\n"
        "Quotas IA les plus élevés",
        {Feature.SEARCH: 120, Feature.RECIPE: 20, Feature.PHOTO: 20, Feature.RECEIPT: 15,
         Feature.PLANNER: 6},
    ),
]  # fmt: skip


class Command(BaseCommand):
    help = "Crée les formules Gratuit, Plus et Famille et leurs quotas (sans écraser)."

    def handle(self, *args, **options):
        created = 0
        for position, row in enumerate(PLANS):
            slug, name, tagline, monthly, yearly, deep, default, highlighted, features, quotas = row
            plan, new = Plan.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "tagline": tagline,
                    "monthly_price": Decimal(monthly),
                    "yearly_price": Decimal(yearly),
                    "deep_mode": deep,
                    "is_default": default,
                    "is_highlighted": highlighted,
                    "features": features,
                    "position": position,
                },
            )
            created += new
            for feature, daily in quotas.items():
                PlanQuota.objects.get_or_create(
                    plan=plan, feature=feature, defaults={"daily": daily}
                )
        PaymentSettings.load()
        self.stdout.write(self.style.SUCCESS(f"{created} formule(s) créée(s)."))
