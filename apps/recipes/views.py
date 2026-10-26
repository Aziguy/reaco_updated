from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.integrations.impactco2 import seasonal_slugs
from apps.pantry.models import PantryItem
from apps.pricing.estimator import estimate_near

from .forms import RecipeFilterForm, ServingsForm
from .metrics import basket_lines
from .models import Favorite, Recipe

PAGE_SIZE = 12


def recipe_list(request):
    form = RecipeFilterForm(request.GET or None)
    recipes = form.filter(Recipe.objects.published().prefetch_related("diets"))
    page = Paginator(recipes, PAGE_SIZE).get_page(request.GET.get("page"))
    template = "recipes/_results.html" if request.htmx else "recipes/list.html"
    return render(request, template, {"form": form, "page": page})


def _servings(request, recipe: Recipe) -> int:
    form = ServingsForm(request.GET)
    if form.is_valid():
        return form.cleaned_data["servings"]
    if request.user.is_authenticated and "servings" not in request.GET:
        return request.user.household_size
    return recipe.servings


def _ingredients_context(request, recipe: Recipe, servings: int) -> dict:
    factor = Decimal(servings) / recipe.servings
    in_pantry: set[int] = set()
    if request.user.is_authenticated:
        in_pantry = set(
            PantryItem.objects.filter(user=request.user)
            .in_stock()
            .values_list("ingredient_id", flat=True)
        )
    seasonal = seasonal_slugs(timezone.localdate().month)
    items = [
        {
            "item": item,
            "quantity": item.display_quantity(factor),
            "in_pantry": item.ingredient_id in in_pantry,
            "seasonal": bool(item.ingredient.impactco2_slug)
            and item.ingredient.impactco2_slug in seasonal,
        }
        for item in recipe.items.all()
    ]
    return {"recipe": recipe, "servings": servings, "items": items}


def recipe_detail(request, slug):
    recipe = get_object_or_404(
        Recipe.objects.published().with_relations().prefetch_related("steps"), slug=slug
    )
    servings = _servings(request, recipe)
    context = _ingredients_context(request, recipe, servings)
    if request.htmx and request.htmx.target == "ingredients":
        return render(request, "recipes/_ingredients.html", context)
    if request.user.is_authenticated:
        context["is_favorite"] = Favorite.objects.filter(user=request.user, recipe=recipe).exists()
        context["lists"] = request.user.shopping_lists.filter(is_archived=False)
    return render(request, "recipes/detail.html", context)


def recipe_prices(request, slug):
    recipe = get_object_or_404(Recipe.objects.published().with_relations(), slug=slug)
    servings = _servings(request, recipe)
    near = request.user.location if request.user.is_authenticated else None
    basket, local = estimate_near(basket_lines(recipe, servings), near)
    context = {
        "recipe": recipe,
        "servings": servings,
        "basket": basket,
        "near": near,
        "local": local,
        "per_serving": basket.total / servings if basket.total else None,
    }
    return render(request, "recipes/_prices.html", context)


@login_required
@require_POST
def toggle_favorite(request, slug):
    recipe = get_object_or_404(Recipe.objects.published(), slug=slug)
    favorite, created = Favorite.objects.get_or_create(user=request.user, recipe=recipe)
    if not created:
        favorite.delete()
    return render(request, "recipes/_favorite.html", {"recipe": recipe, "is_favorite": created})


@login_required
def favorites(request):
    recipes = Recipe.objects.published().filter(favorites__user=request.user)
    return render(request, "recipes/favorites.html", {"recipes": recipes.order_by("title")})
