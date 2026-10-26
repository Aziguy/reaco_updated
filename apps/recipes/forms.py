from django import forms
from django.db.models import F, Q

from .models import Diet, Recipe

SORTS = {
    "recent": ("Les plus récentes", ["-created_at"]),
    "cheap": ("Les moins chères", [F("cost_per_serving").asc(nulls_last=True)]),
    "quick": ("Les plus rapides", [F("prep_minutes") + F("cook_minutes")]),
    "low_co2": ("Faible empreinte carbone", [F("co2_per_serving").asc(nulls_last=True)]),
}
TIMES = [
    ("", "Peu importe"),
    ("20", "20 min ou moins"),
    ("45", "45 min ou moins"),
    ("90", "1 h 30 ou moins"),
]


class RecipeFilterForm(forms.Form):
    q = forms.CharField(label="Recherche", required=False, max_length=100)
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
    sort = forms.ChoiceField(
        label="Trier par",
        required=False,
        choices=[(key, label) for key, (label, _) in SORTS.items()],
    )

    def filter(self, queryset):
        if not self.is_valid():
            return queryset
        data = self.cleaned_data
        if data["q"]:
            queryset = queryset.filter(
                Q(title__icontains=data["q"])
                | Q(summary__icontains=data["q"])
                | Q(items__ingredient__name__icontains=data["q"])
            ).distinct()
        if data["course"]:
            queryset = queryset.filter(course=data["course"])
        if data["diet"]:
            queryset = queryset.filter(diets=data["diet"])
        if data["difficulty"]:
            queryset = queryset.filter(difficulty__lte=data["difficulty"])
        if data["max_minutes"]:
            queryset = queryset.alias(total=F("prep_minutes") + F("cook_minutes")).filter(
                total__lte=data["max_minutes"]
            )
        return queryset.order_by(*SORTS[data["sort"] or "recent"][1])


class ServingsForm(forms.Form):
    servings = forms.IntegerField(min_value=1, max_value=30)
