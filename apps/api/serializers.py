from rest_framework import serializers

from apps.pantry.models import PantryItem
from apps.recipes.models import Ingredient, Recipe, RecipeIngredient
from apps.shopping.models import ShoppingItem, ShoppingList


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ["id", "name", "slug", "aisle", "price_unit", "off_category", "is_staple"]


class RecipeIngredientSerializer(serializers.ModelSerializer):
    ingredient = IngredientSerializer()

    class Meta:
        model = RecipeIngredient
        fields = ["ingredient", "quantity", "unit", "note"]


class RecipeListSerializer(serializers.ModelSerializer):
    diets = serializers.SlugRelatedField(slug_field="slug", many=True, read_only=True)
    url = serializers.HyperlinkedIdentityField(view_name="api:recipe-detail", lookup_field="slug")

    class Meta:
        model = Recipe
        fields = [
            "url",
            "slug",
            "title",
            "summary",
            "course",
            "difficulty",
            "servings",
            "prep_minutes",
            "cook_minutes",
            "diets",
            "image",
            "cost_per_serving",
            "price_coverage",
            "co2_per_serving",
        ]


class RecipeDetailSerializer(RecipeListSerializer):
    items = RecipeIngredientSerializer(many=True)
    steps = serializers.SlugRelatedField(slug_field="text", many=True, read_only=True)

    class Meta(RecipeListSerializer.Meta):
        fields = [
            *RecipeListSerializer.Meta.fields,
            "origin",
            "cuisine",
            "kcal",
            "proteins_g",
            "fat_g",
            "carbs_g",
            "items",
            "steps",
        ]


class OfferSerializer(serializers.Serializer):
    brand = serializers.CharField()
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    coverage = serializers.IntegerField()


class EstimateLineSerializer(serializers.Serializer):
    ingredient = serializers.CharField(source="ingredient.name")
    base_quantity = serializers.DecimalField(max_digits=10, decimal_places=3, allow_null=True)
    unit_price = serializers.DecimalField(max_digits=10, decimal_places=3, allow_null=True)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2, allow_null=True)
    observations = serializers.IntegerField()


class EstimateSerializer(serializers.Serializer):
    total = serializers.DecimalField(max_digits=10, decimal_places=2)
    coverage = serializers.IntegerField()
    lines = EstimateLineSerializer(many=True)
    offers = OfferSerializer(many=True)


class PantryItemSerializer(serializers.ModelSerializer):
    days_left = serializers.IntegerField(read_only=True)

    class Meta:
        model = PantryItem
        fields = [
            "id",
            "name",
            "brand",
            "barcode",
            "ingredient",
            "quantity",
            "unit",
            "expires_on",
            "days_left",
            "estimated_value",
            "status",
            "closed_on",
        ]
        read_only_fields = ["closed_on"]


class ShoppingItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShoppingItem
        fields = ["id", "label", "ingredient", "quantity", "unit", "is_checked"]


class ShoppingListSerializer(serializers.ModelSerializer):
    items = ShoppingItemSerializer(many=True, read_only=True)

    class Meta:
        model = ShoppingList
        fields = ["id", "name", "is_archived", "created_at", "updated_at", "items"]


class AddRecipeSerializer(serializers.Serializer):
    recipe = serializers.SlugRelatedField(slug_field="slug", queryset=Recipe.objects.published())
    servings = serializers.IntegerField(min_value=1, max_value=30)
    use_pantry = serializers.BooleanField(default=True)


class ProductSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    brand = serializers.CharField()
    quantity = serializers.CharField()
    image_url = serializers.CharField()
    nutriscore = serializers.CharField()
    green_score = serializers.CharField()
    nova = serializers.IntegerField(allow_null=True)
