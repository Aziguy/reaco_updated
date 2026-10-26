from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import BarcodeForm, PantryItemForm
from .models import PantryItem
from .services import lookup_barcode, stats_for, suggest_recipes

CHANGED = "pantry-changed"


def _groups(items):
    groups = {"expired": [], "soon": [], "ok": [], "none": []}
    for item in items:
        groups[item.urgency].append(item)
    return groups


@login_required
def pantry_list(request):
    items = PantryItem.objects.filter(user=request.user).in_stock().select_related("ingredient")
    closed = PantryItem.objects.filter(user=request.user).exclude(status=PantryItem.Status.IN_STOCK)
    context = {
        "groups": _groups(items),
        "count": len(items),
        "stats": stats_for(request.user),
        "recent": closed.order_by("-closed_on", "-updated_at")[:8],
    }
    return render(request, "pantry/list.html", context)


@login_required
def pantry_stats(request):
    return render(request, "pantry/_stats.html", {"stats": stats_for(request.user)})


@login_required
def pantry_form(request, pk=None):
    item = get_object_or_404(PantryItem, pk=pk, user=request.user) if pk else None
    form = PantryItemForm(request.POST or None, instance=item)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.user = request.user
        item.save()
        messages.success(request, f"« {item.name} » est enregistré dans votre garde-manger.")
        return redirect("pantry:list")
    return render(
        request, "pantry/form.html", {"form": form, "item": item, "barcode": BarcodeForm()}
    )


@login_required
def pantry_lookup(request):
    barcode = BarcodeForm(request.GET)
    form, error = PantryItemForm(), None
    if not barcode.is_valid():
        error = "Code-barres invalide (8 à 14 chiffres)."
    elif data := lookup_barcode(barcode.cleaned_data["code"]):
        form = PantryItemForm(initial=data)
    else:
        error = "Produit introuvable sur Open Food Facts. Complétez la fiche manuellement."
        form = PantryItemForm(initial={"barcode": barcode.data.get("code", "")})
    return render(request, "pantry/_form.html", {"form": form, "error": error})


@login_required
@require_POST
def pantry_close(request, pk, status):
    item = get_object_or_404(PantryItem, pk=pk, user=request.user)
    if status not in {PantryItem.Status.CONSUMED, PantryItem.Status.WASTED}:
        return HttpResponse(status=400)
    item.close(status)
    if request.htmx:
        return HttpResponse(headers={"HX-Trigger": CHANGED})
    return redirect("pantry:list")


@login_required
@require_POST
def pantry_delete(request, pk):
    get_object_or_404(PantryItem, pk=pk, user=request.user).delete()
    if request.htmx:
        return HttpResponse(headers={"HX-Trigger": CHANGED})
    return redirect("pantry:list")


def suggestions(request):
    context = {}
    if request.user.is_authenticated:
        context = {
            "suggestions": suggest_recipes(request.user, limit=12),
            "expiring": PantryItem.objects.filter(user=request.user).expiring(),
        }
    return render(request, "pantry/suggestions.html", context)
