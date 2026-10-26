import json
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.text import make_slug
from apps.integrations.impactco2 import safe_food_footprints
from apps.recipes import metrics
from apps.recipes.models import Diet, Ingredient, Recipe, RecipeIngredient, RecipeStep

DEMO_DIR = Path(settings.BASE_DIR) / "demo"


class Command(BaseCommand):
    help = "Charge les recettes et ingrédients de démonstration (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-images", action="store_true", help="Remplace les images existantes."
        )

    @transaction.atomic
    def handle(self, *args, refresh_images=False, **options):
        self.refresh_images = refresh_images
        data = json.loads((DEMO_DIR / "recipes.json").read_text(encoding="utf-8"))
        self.credits = json.loads((DEMO_DIR / "images" / "credits.json").read_text("utf-8"))
        ciqual = json.loads((DEMO_DIR / "ciqual.json").read_text("utf-8"))["foods"]
        diets = {
            name: Diet.objects.get_or_create(slug=make_slug(name), defaults={"name": name})[0]
            for name in data["diets"]
        }
        ingredients = {}
        for row in data["ingredients"]:
            food = ciqual.get(row.get("ciqual", ""), {})
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
                    "ciqual_code": row.get("ciqual", ""),
                    "kcal_100g": food.get("kcal"),
                    "proteins_100g": food.get("proteins"),
                    "fat_100g": food.get("fat"),
                    "carbs_100g": food.get("carbs"),
                },
            )
        footprints = safe_food_footprints()
        for row in data["recipes"]:
            recipe = self._recipe(row, ingredients)
            recipe.diets.set(diets[name] for name in row["diets"])
            metrics.refresh(Recipe.objects.with_relations().get(pk=recipe.pk), footprints)
        self.stdout.write(
            self.style.SUCCESS(f"{len(ingredients)} ingrédients, {len(data['recipes'])} recettes.")
        )

    def _credit(self, image: str) -> dict:
        credit = self.credits.get(image)
        if not credit:
            return {"image_credit": "Illustration Comégusto", "image_license": "Licence MIT"}
        return {
            "image_credit": credit["author"][:200],
            "image_license": credit["license"],
            "image_license_url": credit["license_url"],
            "image_source": credit["source"],
        }

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
                "is_featured": row.get("featured", False),
                **self._credit(row["image"]),
            },
        )
        current = Path(recipe.image.name).name
        if self.refresh_images or not current.startswith(Path(row["image"]).stem):
            with (DEMO_DIR / "images" / row["image"]).open("rb") as handle:
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
