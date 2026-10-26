from django import forms
from django.db.models import F

from apps.core.text import normalize

from .models import Diet, Recipe

SORTS = {
    "recent": ("Les plus récentes", ["-created_at", "-pk"]),
    "cheap": ("Les moins chères", [F("cost_per_serving").asc(nulls_last=True), "title", "pk"]),
    "quick": ("Les plus rapides", [F("prep_minutes") + F("cook_minutes"), "title", "pk"]),
    "low_co2": (
        "Faible empreinte carbone",
        [F("co2_per_serving").asc(nulls_last=True), "title", "pk"],
    ),
}
TIMES = [
    ("", "Peu importe"),
    ("20", "20 min ou moins"),
    ("45", "45 min ou moins"),
    ("90", "1 h 30 ou moins"),
]
SECONDARY = ("course", "diet", "difficulty", "max_minutes")


class RecipeFilterForm(forms.Form):
    q = forms.CharField(label="Recherche", required=False, max_length=100)
    sort = forms.ChoiceField(
        label="Trier par",
        required=False,
        choices=[("" if key == "recent" else key, label) for key, (label, _) in SORTS.items()],
    )
    course = forms.ChoiceField(
        label="Type de plat", required=False, choices=[("", "Tous"), *Recipe.Course.choices]
    )
    diet = forms.ModelChoiceField(
        label="Régime",
        required=False,
        queryset=Diet.objects.all(),
        to_field_name="slug",
        empty_label="Tous",
    )
    difficulty = forms.TypedChoiceField(
        label="Difficulté max.",
        required=False,
        coerce=int,
        empty_value=None,
        choices=[("", "Toutes"), *Recipe.Difficulty.choices],
    )
    max_minutes = forms.TypedChoiceField(
        label="Temps total", required=False, coerce=int, empty_value=None, choices=TIMES
    )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data if data is not None else {}, *args, **kwargs)
        self.fields["q"].widget.attrs.update(
            {"type": "search", "placeholder": "Plat, ingrédient…", "autocomplete": "off"}
        )

    @property
    def secondary_active(self) -> int:
        return sum(1 for name in SECONDARY if self.data.get(name))

    def filter(self, queryset):
        self.is_valid()
        data = self.cleaned_data
        for word in normalize(data.get("q") or "").split():
            queryset = queryset.filter(search_text__contains=word)
        if data.get("course"):
            queryset = queryset.filter(course=data["course"])
        if data.get("diet"):
            queryset = queryset.filter(diets=data["diet"])
        if data.get("difficulty"):
            queryset = queryset.filter(difficulty__lte=data["difficulty"])
        if data.get("max_minutes"):
            queryset = queryset.alias(total=F("prep_minutes") + F("cook_minutes")).filter(
                total__lte=data["max_minutes"]
            )
        return queryset.order_by(*SORTS[data.get("sort") or "recent"][1])


class ServingsForm(forms.Form):
    servings = forms.IntegerField(min_value=1, max_value=30)
