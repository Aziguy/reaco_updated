"""Catalogue growth from the admin: dishes the catalogue lacks, then their recipes as drafts."""

from django import forms
from unfold.widgets import (
    UnfoldAdminIntegerFieldWidget,
    UnfoldAdminSelectWidget,
    UnfoldAdminTextareaWidget,
)

from apps.recipes.models import Recipe

from .generator import Brief, generate
from .models import Feature, Mode
from .providers import Prompt, clean_text
from .services import Caller, ask

MAX_DISHES = 20

SYSTEM = """Tu aides l'équipe de Comégusto à compléter son catalogue de recettes économiques, \
familiales et anti-gaspi, cuisinées en France avec des ingrédients faciles à trouver.

- dishes : des plats populaires et appréciés, absents des recettes existantes (ni doublon, ni \
simple variante).
- name : nom usuel du plat en français, court (« Poulet yassa », « Dal de lentilles corail »).
- why : une phrase qui dit pourquoi il plaira (prix, rapidité, saison, restes utilisés)."""

SCHEMA = {
    "type": "object",
    "properties": {
        "dishes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"name": {"type": "string"}, "why": {"type": "string"}},
                "required": ["name", "why"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["dishes"],
    "additionalProperties": False,
}


def suggest_dishes(count: int, cuisine: str, course: str, caller: Caller) -> list[dict]:
    titles = "; ".join(Recipe.objects.order_by("title").values_list("title", flat=True))
    lines = [f"Propose {count} plats."]
    if cuisine:
        lines.append(f"Cuisine : {Recipe.Cuisine(cuisine).label}.")
    if course:
        lines.append(f"Type de plat : {Recipe.Course(course).label}.")
    prompt = Prompt(
        system=f"{SYSTEM}\n\nRecettes existantes : {titles}",
        text="\n".join(lines),
        schema=SCHEMA,
    )
    data = ask(Feature.CATALOG, Mode.FAST, caller, prompt)
    existing = {title.lower() for title in Recipe.objects.values_list("title", flat=True)}
    dishes = []
    for row in (data.get("dishes") or [])[:MAX_DISHES]:
        name = clean_text(row.get("name"), 120)
        if name and name.lower() not in existing:
            dishes.append({"name": name, "why": clean_text(row.get("why"), 200)})
    return dishes


def generate_dish(name: str, servings: int, cuisine: str, mode: str, caller: Caller) -> Recipe:
    brief = Brief(servings=servings, dish=name, cuisine=cuisine)
    return generate(brief, mode, caller, feature=Feature.CATALOG, review=True)


def _select(choices):
    return forms.ChoiceField(
        required=False, choices=[("", "Toutes"), *choices], widget=UnfoldAdminSelectWidget
    )


class SuggestForm(forms.Form):
    cuisine = _select(Recipe.Cuisine.choices)
    course = _select(Recipe.Course.choices)
    count = forms.IntegerField(
        label="Nombre de plats",
        min_value=3,
        max_value=MAX_DISHES,
        initial=8,
        widget=UnfoldAdminIntegerFieldWidget,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuisine"].label = "Cuisine"
        self.fields["course"].label = "Type de plat"


class GenerateForm(forms.Form):
    dishes = forms.CharField(
        label="Plats à créer",
        help_text=f"Un plat par ligne, {MAX_DISHES} au plus.",
        widget=UnfoldAdminTextareaWidget(attrs={"rows": 8, "placeholder": "Poulet yassa\nDal"}),
    )
    cuisine = _select(Recipe.Cuisine.choices)
    servings = forms.IntegerField(
        label="Portions", min_value=1, max_value=12, initial=4, widget=UnfoldAdminIntegerFieldWidget
    )
    mode = forms.ChoiceField(
        label="Mode", choices=Mode.choices, initial=Mode.FAST, widget=UnfoldAdminSelectWidget
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cuisine"].label = "Cuisine"

    def clean_dishes(self):
        names = []
        for line in self.cleaned_data["dishes"].splitlines():
            name = clean_text(line.strip(" -•*\t"), 120)
            if name and name.lower() not in {n.lower() for n in names}:
                names.append(name)
        if not names:
            raise forms.ValidationError("Indiquez au moins un plat.")
        if len(names) > MAX_DISHES:
            raise forms.ValidationError(f"{MAX_DISHES} plats au plus à la fois.")
        return names
