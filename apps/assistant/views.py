from datetime import timedelta
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.pantry.models import PantryItem
from apps.recipes.models import Recipe, RecipeIngredient

from . import planner
from .forms import FridgeForm, MealPlanForm, ReceiptForm, ReceiptLineFormSet
from .generator import GenerationError, create_recipe
from .models import Feature, MealPlan, Mode, PlannedMeal
from .receipts import ReceiptError, read_receipt
from .search import MAX_LENGTH, Criteria, apply, classic_query, interpret
from .services import Caller, Unavailable, get_route, remaining

EXAMPLES = [
    "Un dîner végétarien pour 4 à moins de 10 €",
    "Que faire avec mes courgettes et des œufs ?",
    "Un plat indien végétarien et pas cher",
    "Un plat sans gluten, faible en CO2",
]


def _mode(value) -> str:
    return value if value in Mode.values else Mode.FAST


def _remaining(request, feature: str) -> int | None:
    route = get_route(feature, Mode.FAST)
    return remaining(route, Caller.from_request(request)) if route else None


def hub(request):
    context = {"examples": EXAMPLES, "search_left": _remaining(request, Feature.SEARCH)}
    if request.user.is_authenticated:
        context["plans"] = request.user.meal_plans.filter(status=MealPlan.Status.READY)[:3]
        context["creations"] = Recipe.objects.filter(
            author=request.user, is_ai_generated=True
        ).order_by("-created_at")[:3]
    return render(request, "assistant/hub.html", context)


def search(request):
    text = " ".join(request.GET.get("demande", "").split())[:MAX_LENGTH]
    mode = _mode(request.GET.get("mode"))
    token = request.GET.get("c", "")
    criteria = Criteria.from_token(token) if token else None
    context = {"text": text, "mode": mode, "examples": EXAMPLES}
    if criteria is None and text and not request.htmx:
        context["lazy_url"] = f"{request.path}?{urlencode({'demande': text, 'mode': mode})}"
        context["search_left"] = _remaining(request, Feature.SEARCH)
        return render(request, "assistant/search.html", context)

    notice = ""
    if criteria is None and text:
        criteria, notice = interpret(text, mode, Caller.from_request(request))
    if criteria is not None:
        recipes, relaxed = apply(criteria, request.user if request.user.is_authenticated else None)
        context.update(
            criteria=criteria,
            recipes=recipes,
            relaxed=relaxed,
            notice=notice,
            classic=classic_query(criteria),
            link_query=f"?servings={criteria.servings}" if criteria.servings else "",
            needs_login=criteria.use_pantry and not request.user.is_authenticated,
        )
    context["search_left"] = _remaining(request, Feature.SEARCH)
    if not request.htmx:
        return render(request, "assistant/search.html", context)
    response = render(request, "assistant/_search_results.html", context)
    if criteria is not None:
        query = urlencode({"demande": text, "mode": mode, "c": criteria.token})
        response["HX-Replace-Url"] = f"{request.path}?{query}"
    return response


@login_required
def plan_new(request):
    form = MealPlanForm(request.POST or None, initial={"servings": request.user.household_size})
    if request.method == "POST" and form.is_valid():
        plan = form.save(commit=False)
        plan.user = request.user
        plan.mode = form.cleaned_data["mode"]
        plan.save()
        return redirect(plan)
    plans = request.user.meal_plans.filter(status=MealPlan.Status.READY).prefetch_related(
        Prefetch("meals", PlannedMeal.objects.select_related("recipe"))
    )[:6]
    return render(
        request,
        "assistant/plan_new.html",
        {"form": form, "plans": plans, "plan_left": _remaining(request, Feature.PLANNER)},
    )


def _plan_context(plan: MealPlan) -> dict:
    meals = list(
        plan.meals.select_related("recipe").prefetch_related(
            Prefetch("recipe__items", RecipeIngredient.objects.select_related("ingredient"))
        )
    )
    start = plan.created_at.date()
    days = []
    for meal in meals:
        if not days or days[-1]["number"] != meal.day:
            date = start + timedelta(days=meal.day - 1)
            days.append({"number": meal.day, "date": date, "meals": []})
        days[-1]["meals"].append(meal)
    return {"plan": plan, "days": days, "totals": planner.totals(plan, meals)}


def _user_plan(request, pk) -> MealPlan:
    return get_object_or_404(MealPlan.objects.select_related("diet"), pk=pk, user=request.user)


@login_required
def plan_detail(request, pk):
    plan = _user_plan(request, pk)
    context = _plan_context(plan) if plan.status == MealPlan.Status.READY else {"plan": plan}
    return render(request, "assistant/plan.html", context)


@login_required
@require_POST
def plan_run(request, pk):
    plan = _user_plan(request, pk)
    if plan.status == MealPlan.Status.PENDING:
        plan = planner.generate(plan, Caller.from_request(request))
    if plan.status == MealPlan.Status.READY:
        return render(request, "assistant/_plan.html", _plan_context(plan))
    return render(request, "assistant/_plan_status.html", {"plan": plan})


@login_required
@require_POST
def meal_swap(request, pk, meal_pk):
    meal = get_object_or_404(
        PlannedMeal.objects.select_related("plan"), pk=meal_pk, plan__pk=pk, plan__user=request.user
    )
    planner.swap(meal)
    return render(request, "assistant/_plan.html", _plan_context(meal.plan))


@login_required
@require_POST
def plan_shopping(request, pk):
    plan = _user_plan(request, pk)
    shopping_list = plan.shopping_list or planner.to_shopping_list(plan)
    messages.success(request, "La liste de courses du menu est prête.")
    return redirect(shopping_list)


@login_required
def fridge(request):
    stock = PantryItem.objects.filter(user=request.user).in_stock()
    initial = {
        "servings": request.user.household_size,
        "products": list(stock.expiring().values_list("pk", flat=True)[:5]),
    }
    form = FridgeForm(request.POST or None, user=request.user, initial=initial)
    error = ""
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            recipe = create_recipe(
                data["products"],
                data["servings"],
                data["wishes"],
                data["mode"],
                Caller.from_request(request),
            )
        except (Unavailable, GenerationError) as exc:
            error = getattr(exc, "message", str(exc))
        else:
            messages.success(request, "Votre recette est prête. Bon appétit !")
            return redirect(f"{recipe.get_absolute_url()}?servings={recipe.servings}")
    return render(
        request,
        "assistant/fridge.html",
        {
            "form": form,
            "error": error,
            "has_stock": stock.exists(),
            "recipe_left": _remaining(request, Feature.RECIPE),
        },
    )


@login_required
@require_POST
def propose(request, slug):
    recipe = get_object_or_404(Recipe, slug=slug, author=request.user, is_ai_generated=True)
    if not recipe.review_requested:
        recipe.review_requested = True
        recipe.save(update_fields=["review_requested", "updated_at"])
    messages.success(request, "Merci ! L'équipe relira votre recette avant de la publier.")
    return redirect(recipe)


@login_required
def receipt(request):
    form = ReceiptForm(request.POST or None, request.FILES or None)
    error = ""
    if request.method == "POST" and form.is_valid():
        try:
            result = read_receipt(
                form.cleaned_data["photo"], form.cleaned_data["mode"], Caller.from_request(request)
            )
        except (Unavailable, ReceiptError) as exc:
            error = getattr(exc, "message", str(exc))
        else:
            formset = ReceiptLineFormSet(initial=result["lines"])
            return render(request, "assistant/receipt_review.html", {**result, "formset": formset})
    return render(
        request,
        "assistant/receipt.html",
        {"form": form, "error": error, "receipt_left": _remaining(request, Feature.RECEIPT)},
    )


@login_required
@require_POST
def receipt_save(request):
    formset = ReceiptLineFormSet(request.POST)
    if not formset.is_valid():
        return render(request, "assistant/receipt_review.html", {"formset": formset})
    items = [
        PantryItem(
            user=request.user,
            name=data["name"],
            ingredient=data.get("ingredient"),
            quantity=data.get("quantity"),
            unit=data["unit"],
            estimated_value=data.get("estimated_value"),
            expires_on=data.get("expires_on"),
        )
        for data in formset.cleaned_data
        if data.get("selected")
    ]
    PantryItem.objects.bulk_create(items)
    messages.success(request, f"{len(items)} produit(s) ajouté(s) à votre garde-manger.")
    return redirect("pantry:list")
