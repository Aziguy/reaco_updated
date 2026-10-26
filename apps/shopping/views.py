from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.pantry.models import PantryItem
from apps.pricing.estimator import estimate_near
from apps.recipes.models import Ingredient
from apps.recipes.units import Unit

from . import services
from .forms import AddRecipeForm, ShoppingItemForm, ShoppingListForm
from .models import ShoppingItem, ShoppingList

CHANGED = "shopping-changed"


def _user_list(request, pk) -> ShoppingList:
    return get_object_or_404(ShoppingList, pk=pk, user=request.user)


def _aisles(shopping_list):
    items = sorted(
        shopping_list.items.select_related("ingredient"),
        key=lambda i: (i.aisle, i.is_checked, i.label),
    )
    return [(aisle, list(group)) for aisle, group in groupby(items, key=lambda i: i.aisle)]


@login_required
def index(request):
    form = ShoppingListForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        shopping_list = form.save(commit=False)
        shopping_list.user = request.user
        shopping_list.save()
        return redirect(shopping_list)
    lists = request.user.shopping_lists.all()
    return render(request, "shopping/index.html", {"lists": lists, "form": form})


@login_required
def detail(request, pk):
    shopping_list = _user_list(request, pk)
    context = {"list": shopping_list, "aisles": _aisles(shopping_list), "form": ShoppingItemForm()}
    return render(request, "shopping/detail.html", context)


@login_required
@require_POST
def add_item(request, pk):
    shopping_list = _user_list(request, pk)
    form = ShoppingItemForm(request.POST)
    if form.is_valid():
        item = form.save(commit=False)
        item.shopping_list = shopping_list
        item.ingredient = Ingredient.objects.filter(name__iexact=item.label.strip()).first()
        item.save()
    return redirect(shopping_list)


@login_required
@require_POST
def toggle_item(request, pk):
    item = get_object_or_404(ShoppingItem, pk=pk, shopping_list__user=request.user)
    item.is_checked = not item.is_checked
    item.save(update_fields=["is_checked"])
    if request.htmx:
        response = render(request, "shopping/_item.html", {"item": item})
        response["HX-Trigger"] = CHANGED
        return response
    return redirect(item.shopping_list)


@login_required
@require_POST
def delete_item(request, pk):
    item = get_object_or_404(ShoppingItem, pk=pk, shopping_list__user=request.user)
    item.delete()
    if request.htmx:
        return HttpResponse(headers={"HX-Trigger": CHANGED})
    return redirect(item.shopping_list)


@login_required
def compare(request, pk):
    shopping_list = _user_list(request, pk)
    near = request.user.location
    basket, local = estimate_near(services.basket_lines(shopping_list), near)
    context = {"basket": basket, "near": near, "local": local}
    return render(request, "shopping/_compare.html", context)


@login_required
def print_view(request, pk):
    shopping_list = _user_list(request, pk)
    return render(
        request, "shopping/print.html", {"list": shopping_list, "aisles": _aisles(shopping_list)}
    )


@login_required
@require_POST
def add_recipe(request):
    form = AddRecipeForm(request.POST, user=request.user)
    if not form.is_valid():
        messages.error(request, "Impossible d'ajouter cette recette.")
        return redirect("recipes:list")
    data = form.cleaned_data
    shopping_list = data["shopping_list"] or ShoppingList.objects.create(
        user=request.user, name=f"Courses : {data['recipe'].title}"[:120]
    )
    result = services.add_recipe(
        shopping_list, data["recipe"], data["servings"], use_pantry=data["use_pantry"]
    )
    summary = f"{result.added} article(s) ajouté(s), {result.merged} complété(s)"
    if result.in_pantry:
        summary += f", {result.in_pantry} déjà dans votre garde-manger"
    messages.success(request, summary + ".")
    return redirect(shopping_list)


@login_required
@require_POST
@transaction.atomic
def checkout(request, pk):
    """Move checked items to the pantry so they can be tracked until consumed."""
    shopping_list = _user_list(request, pk)
    checked = list(shopping_list.items.filter(is_checked=True))
    PantryItem.objects.bulk_create(
        PantryItem(
            user=request.user,
            ingredient=item.ingredient,
            name=item.label,
            quantity=item.quantity,
            unit=item.unit or Unit.PIECE,
        )
        for item in checked
    )
    ShoppingItem.objects.filter(pk__in=[item.pk for item in checked]).delete()
    count = len(checked)
    messages.success(
        request,
        f"{count} article(s) rangé(s) dans le garde-manger. Ajoutez leurs dates de péremption.",
    )
    return redirect("pantry:list")


@login_required
@require_POST
def archive(request, pk):
    shopping_list = _user_list(request, pk)
    shopping_list.is_archived = not shopping_list.is_archived
    shopping_list.save(update_fields=["is_archived", "updated_at"])
    return redirect("shopping:index")


@login_required
@require_POST
def delete(request, pk):
    _user_list(request, pk).delete()
    messages.success(request, "Liste supprimée.")
    return redirect("shopping:index")
