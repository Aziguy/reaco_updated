from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver

from .models import Recipe, RecipeIngredient


@receiver(post_save, sender=RecipeIngredient)
@receiver(post_delete, sender=RecipeIngredient)
def ingredient_changed(sender, instance, **kwargs):
    recipe = Recipe.objects.filter(pk=instance.recipe_id).first()
    if recipe:
        recipe.refresh_search()


@receiver(m2m_changed, sender=Recipe.diets.through)
def diets_changed(sender, instance, action, **kwargs):
    if action in {"post_add", "post_remove", "post_clear"} and isinstance(instance, Recipe):
        instance.refresh_search()
