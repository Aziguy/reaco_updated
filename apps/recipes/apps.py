from django.apps import AppConfig


class RecipesConfig(AppConfig):
    name = "apps.recipes"
    verbose_name = "Recettes"

    def ready(self):
        from . import signals  # noqa: F401
