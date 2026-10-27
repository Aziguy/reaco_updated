from urllib.parse import urlencode

from django.shortcuts import render

from .models import Feature, Mode
from .search import MAX_LENGTH, Criteria, apply, classic_query, interpret
from .services import Caller, get_route, remaining

EXAMPLES = [
    "Un dîner végétarien pour 4 à moins de 10 €",
    "Que faire avec mes courgettes et des œufs ?",
    "Une soupe rapide et pas chère",
    "Un plat sans gluten, faible en CO2",
]


def _mode(value) -> str:
    return value if value in Mode.values else Mode.FAST


def _remaining(request, feature: str) -> int | None:
    route = get_route(feature, Mode.FAST)
    return remaining(route, Caller.from_request(request)) if route else None


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
