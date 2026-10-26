from django import forms

from apps.recipes.models import Recipe

from .models import ShoppingItem, ShoppingList


class ShoppingListForm(forms.ModelForm):
    class Meta:
        model = ShoppingList
        fields = ["name"]


class ShoppingItemForm(forms.ModelForm):
    class Meta:
        model = ShoppingItem
        fields = ["label", "quantity", "unit"]
        widgets = {"unit": forms.Select(attrs={"class": "input w-32"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["unit"].choices = [("", "Unité"), *self.fields["unit"].choices[1:]]


class AddRecipeForm(forms.Form):
    recipe = forms.ModelChoiceField(queryset=Recipe.objects.published(), widget=forms.HiddenInput)
    servings = forms.IntegerField(label="Portions", min_value=1, max_value=30)
    shopping_list = forms.ModelChoiceField(
        label="Liste",
        queryset=ShoppingList.objects.none(),
        required=False,
        empty_label="Nouvelle liste",
    )
    use_pantry = forms.BooleanField(label="Déduire mon garde-manger", required=False, initial=True)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shopping_list"].queryset = ShoppingList.objects.filter(
            user=user, is_archived=False
        )
