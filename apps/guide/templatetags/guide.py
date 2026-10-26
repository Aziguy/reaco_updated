import json
from functools import cache

from django import template
from django.contrib.staticfiles import finders

from apps.guide.content import FIGURES

register = template.Library()

MANIFEST = "img/guide/manifest.json"


@cache
def manifest() -> dict:
    path = finders.find(MANIFEST)
    if not path:
        return {}
    with open(path, encoding="utf-8") as file:
        return json.load(file)


@register.inclusion_tag("guide/_figure.html")
def guide_figure(name: str):
    figure = FIGURES[name]
    size = manifest().get(name, {})
    return {
        "figure": figure,
        "light": f"img/guide/{name}-light.webp",
        "dark": f"img/guide/{name}-dark.webp",
        "width": size.get("width"),
        "height": size.get("height"),
    }
