from django.core.management.base import BaseCommand

from apps.recipes import metrics


class Command(BaseCommand):
    help = "Recalcule le coût par portion et l'empreinte carbone des recettes."

    def handle(self, *args, **options):
        count = metrics.refresh_all()
        self.stdout.write(self.style.SUCCESS(f"{count} recette(s) mise(s) à jour."))
