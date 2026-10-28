from django.contrib import messages
from django.shortcuts import render
from django.template.response import TemplateResponse

from apps.recipes.models import Ingredient

from .catalog import GenerateForm, SuggestForm, generate_dish, suggest_dishes
from .generator import GenerationError
from .models import Mode
from .services import Caller, Unavailable


def generate_page(model_admin, request):
    """Suggest missing dishes, then queue their generation one row at a time."""
    action = request.POST.get("action") if request.method == "POST" else ""
    suggest_form = SuggestForm(request.POST if action == "suggest" else None, prefix="s")
    generate_form = GenerateForm(request.POST if action == "generate" else None, prefix="g")
    context = {
        **model_admin.admin_site.each_context(request),
        "title": "Générer des recettes avec l'IA",
        "opts": model_admin.model._meta,
        "suggest_form": suggest_form,
        "generate_form": generate_form,
        "drafts": Ingredient.objects.filter(is_draft=True).count(),
    }
    if action == "suggest" and suggest_form.is_valid():
        data = suggest_form.cleaned_data
        try:
            dishes = suggest_dishes(
                data["count"], data["cuisine"], data["course"], Caller.from_request(request)
            )
        except Unavailable as exc:
            messages.error(request, exc.message)
        else:
            context["dishes"] = dishes
            names = "\n".join(dish["name"] for dish in dishes)
            context["generate_form"] = GenerateForm(
                initial={"dishes": names, "cuisine": data["cuisine"]}, prefix="g"
            )
    if action == "generate" and generate_form.is_valid():
        context["queue"] = generate_form.cleaned_data
    return TemplateResponse(request, "admin/recipes/recipe/generate.html", context)


def generate_one(model_admin, request):
    name = request.POST.get("name", "")[:120]
    mode = request.POST.get("mode") if request.POST.get("mode") in Mode.values else Mode.FAST
    try:
        servings = max(1, min(int(request.POST.get("servings", 4)), 12))
    except ValueError:
        servings = 4
    context = {"name": name}
    try:
        recipe = generate_dish(
            name, servings, request.POST.get("cuisine", ""), mode, Caller.from_request(request)
        )
    except (Unavailable, GenerationError) as exc:
        context["error"] = getattr(exc, "message", str(exc))
    else:
        context["recipe"] = recipe
        context["drafts"] = recipe.items.filter(ingredient__is_draft=True).count()
    return render(request, "admin/recipes/recipe/_generated.html", context)
