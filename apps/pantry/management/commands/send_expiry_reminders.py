from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse

from apps.pantry.models import PantryItem


class Command(BaseCommand):
    help = "Envoie un email aux utilisateurs dont des produits arrivent à péremption."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=2)
        parser.add_argument("--base-url", default="http://localhost:8000")

    def handle(self, *args, days, base_url, **options):
        users = get_user_model().objects.filter(is_active=True, expiry_reminders=True)
        sent = 0
        for user in users.iterator():
            items = list(PantryItem.objects.filter(user=user).expiring(days))
            if not items:
                continue
            context = {
                "user": user,
                "items": items,
                "url": base_url.rstrip("/") + reverse("pantry:suggestions"),
            }
            send_mail(
                f"{len(items)} produit(s) à consommer rapidement",
                render_to_string("pantry/email_reminder.txt", context),
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"{sent} rappel(s) envoyé(s)."))
