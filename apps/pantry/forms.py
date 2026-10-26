from django import forms

from apps.recipes.models import Ingredient

from .models import PantryItem


class PantryItemForm(forms.ModelForm):
    ingredient = forms.ModelChoiceField(
        label="Ingrédient correspondant",
        queryset=Ingredient.objects.all(),
        required=False,
        empty_label="Aucun",
        help_text="Permet de proposer des recettes et de déduire le stock des listes de courses.",
    )

    class Meta:
        model = PantryItem
        fields = [
            "name",
            "brand",
            "ingredient",
            "quantity",
            "unit",
            "expires_on",
            "estimated_value",
            "barcode",
            "image_url",
            "nutriscore",
            "green_score",
        ]
        widgets = {
            "expires_on": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "barcode": forms.HiddenInput,
            "image_url": forms.HiddenInput,
            "nutriscore": forms.HiddenInput,
            "green_score": forms.HiddenInput,
        }

    def clean_image_url(self):
        url = self.cleaned_data["image_url"]
        allowed = ("https://images.openfoodfacts.org/", "https://static.openfoodfacts.org/")
        return url if url.startswith(allowed) else ""


class BarcodeForm(forms.Form):
    code = forms.RegexField(label="Code-barres", regex=r"^\d{8,14}$", max_length=14)
