from django import forms

from apps.pantry.models import PantryItem
from apps.recipes.models import Diet, Ingredient
from apps.recipes.units import Unit

from .models import MealPlan, Mode

MAX_UPLOAD = 8 * 1024 * 1024
IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"}


class ModeField(forms.ChoiceField):
    def __init__(self, **kwargs):
        super().__init__(
            label="Mode",
            choices=Mode.choices,
            initial=Mode.FAST,
            widget=forms.RadioSelect,
            **kwargs,
        )


class MealPlanForm(forms.ModelForm):
    days = forms.TypedChoiceField(
        label="Durée",
        coerce=int,
        choices=[(n, f"{n} jours") for n in range(3, 8)],
        initial=5,
    )
    meals_per_day = forms.TypedChoiceField(
        label="Repas",
        coerce=int,
        choices=[(1, "Dîners"), (2, "Déjeuners et dîners")],
        initial=1,
        widget=forms.RadioSelect,
    )
    diet = forms.ModelChoiceField(
        label="Régime", queryset=Diet.objects.all(), required=False, empty_label="Aucun"
    )
    mode = ModeField()

    class Meta:
        model = MealPlan
        fields = [
            "days", "meals_per_day", "servings", "budget", "diet", "use_pantry", "preferences",
        ]  # fmt: skip
        labels = {"budget": "Budget total (facultatif)", "preferences": "Vos envies (facultatif)"}
        widgets = {
            "servings": forms.NumberInput(attrs={"min": 1, "max": 12}),
            "budget": forms.NumberInput(attrs={"min": 5, "step": 1, "placeholder": "Ex. 60"}),
            "preferences": forms.TextInput(
                attrs={"placeholder": "Ex. un plat de pâtes, pas de poisson, plats rapides"}
            ),
        }

    def clean_servings(self):
        servings = self.cleaned_data["servings"]
        if not 1 <= servings <= 12:
            raise forms.ValidationError("Entre 1 et 12 personnes.")
        return servings


class FridgeForm(forms.Form):
    products = forms.ModelMultipleChoiceField(
        label="Produits à utiliser",
        queryset=PantryItem.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Choisissez au moins un produit."},
    )
    servings = forms.IntegerField(label="Personnes", min_value=1, max_value=12)
    wishes = forms.CharField(
        label="Vos envies (facultatif)",
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={"placeholder": "Ex. sans four, en 20 minutes, épicé"}),
    )
    mode = ModeField()

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["products"].queryset = (
            PantryItem.objects.filter(user=user).in_stock().select_related("ingredient")
        )

    def clean_products(self):
        products = self.cleaned_data["products"]
        if len(products) > 10:
            raise forms.ValidationError("Choisissez au plus 10 produits.")
        return products


class ReceiptForm(forms.Form):
    photo = forms.FileField(label="Photo du ticket")
    mode = ModeField()

    def clean_photo(self):
        photo = self.cleaned_data["photo"]
        if photo.size > MAX_UPLOAD:
            raise forms.ValidationError("Photo trop lourde (8 Mo maximum).")
        if photo.content_type not in IMAGE_TYPES:
            raise forms.ValidationError("Choisissez une photo (JPEG, PNG ou WebP).")
        return photo


class ReceiptLineForm(forms.Form):
    selected = forms.BooleanField(required=False)
    name = forms.CharField(max_length=200)
    ingredient = forms.ModelChoiceField(
        queryset=Ingredient.objects.all(), required=False, widget=forms.HiddenInput
    )
    quantity = forms.DecimalField(
        required=False, min_value=0, max_digits=8, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "any"}),
    )  # fmt: skip
    unit = forms.ChoiceField(choices=Unit.choices)
    estimated_value = forms.DecimalField(
        required=False, min_value=0, max_digits=7, decimal_places=2,
        widget=forms.NumberInput(attrs={"step": "0.01"}),
    )  # fmt: skip
    expires_on = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    )


ReceiptLineFormSet = forms.formset_factory(ReceiptLineForm, extra=0, max_num=40)
