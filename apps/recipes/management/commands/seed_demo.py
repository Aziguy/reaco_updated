import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.text import make_slug
from apps.recipes.models import Diet, Ingredient, Recipe, RecipeIngredient, RecipeStep

DEMO_DIR = Path(settings.BASE_DIR) / "demo"


class Command(BaseCommand):
    help = "Charge les recettes et ingrédients de démonstration (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        data = json.loads((DEMO_DIR / "recipes.json").read_text(encoding="utf-8"))
        diets = {
            name: Diet.objects.get_or_create(slug=make_slug(name), defaults={"name": name})[0]
            for name in data["diets"]
        }
        ingredients = {}
        for row in data["ingredients"]:
            ingredients[row["name"]], _ = Ingredient.objects.update_or_create(
                slug=make_slug(row["name"]),
                defaults={
                    "name": row["name"],
                    "aisle": row["aisle"],
                    "price_unit": row["price_unit"],
                    "unit_weight_g": row.get("unit_weight_g"),
                    "off_category": row.get("off", ""),
                    "impactco2_slug": row.get("co2", ""),
                    "is_staple": row.get("staple", False),
                },
            )
        for row in data["recipes"]:
            recipe = self._recipe(row, ingredients)
            recipe.diets.set(diets[name] for name in row["diets"])
        self.stdout.write(
            self.style.SUCCESS(f"{len(ingredients)} ingrédients, {len(data['recipes'])} recettes.")
        )

    def _recipe(self, row, ingredients):
        recipe, _ = Recipe.objects.update_or_create(
            slug=make_slug(row["title"]),
            defaults={
                "title": row["title"],
                "summary": row["summary"],
                "course": row["course"],
                "difficulty": row["difficulty"],
                "servings": row["servings"],
                "prep_minutes": row["prep"],
                "cook_minutes": row["cook"],
                "origin": row["origin"],
                "kcal": row["kcal"],
                "proteins_g": row["proteins"],
                "fat_g": row["fat"],
                "carbs_g": row["carbs"],
                "is_featured": row["featured"],
            },
        )
        if not recipe.image:
            path = DEMO_DIR / "images" / row["image"]
            with path.open("rb") as handle:
                recipe.image.save(row["image"], File(handle), save=True)
        recipe.items.all().delete()
        RecipeIngredient.objects.bulk_create(
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredients[name],
                quantity=Decimal(str(quantity)),
                unit=unit,
                note=note[0] if note else "",
                position=index,
            )
            for index, (name, quantity, unit, *note) in enumerate(row["ingredients"])
        )
        recipe.steps.all().delete()
        RecipeStep.objects.bulk_create(
            RecipeStep(recipe=recipe, position=index + 1, text=text)
            for index, text in enumerate(row["steps"])
        )
        return recipe
