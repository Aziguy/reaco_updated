from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import mixins, permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from apps.integrations import openfoodfacts
from apps.integrations.http import ServiceError
from apps.pantry.models import PantryItem
from apps.pricing.estimator import estimate_near
from apps.recipes.forms import RecipeFilterForm
from apps.recipes.metrics import basket_lines
from apps.recipes.models import Ingredient, Recipe
from apps.shopping import services as shopping
from apps.shopping.models import ShoppingItem, ShoppingList

from . import serializers


class RecipeViewSet(viewsets.ReadOnlyModelViewSet):
    lookup_field = "slug"

    def get_queryset(self):
        queryset = Recipe.objects.published().with_relations().prefetch_related("steps")
        return RecipeFilterForm(self.request.query_params).filter(queryset)

    def get_serializer_class(self):
        if self.action == "list":
            return serializers.RecipeListSerializer
        return serializers.RecipeDetailSerializer

    @extend_schema(
        parameters=[
            OpenApiParameter("servings", OpenApiTypes.INT),
            OpenApiParameter("lat", OpenApiTypes.FLOAT),
            OpenApiParameter("lon", OpenApiTypes.FLOAT),
            OpenApiParameter("radius_km", OpenApiTypes.FLOAT),
        ],
        responses=serializers.EstimateSerializer,
    )
    @action(detail=True)
    def estimate(self, request, slug=None):
        recipe = self.get_object()
        params = request.query_params
        try:
            servings = min(max(int(params.get("servings", recipe.servings)), 1), 30)
            near = None
            if "lat" in params and "lon" in params:
                radius = min(float(params.get("radius_km", 10)), 100)
                near = (float(params["lat"]), float(params["lon"]), radius)
        except ValueError as exc:
            raise NotFound("Paramètres invalides.") from exc
        basket, _ = estimate_near(basket_lines(recipe, servings), near)
        return Response(serializers.EstimateSerializer(basket).data)


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = serializers.IngredientSerializer
    lookup_field = "slug"


class OwnedMixin:
    permission_classes = [permissions.IsAuthenticated]
    model = None

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.model.objects.none()
        return self.owned(self.model.objects.all())

    def owned(self, queryset):
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class PantryItemViewSet(OwnedMixin, viewsets.ModelViewSet):
    serializer_class = serializers.PantryItemSerializer
    model = PantryItem


class ShoppingListViewSet(OwnedMixin, viewsets.ModelViewSet):
    serializer_class = serializers.ShoppingListSerializer
    model = ShoppingList

    def owned(self, queryset):
        return super().owned(queryset).prefetch_related("items")

    @extend_schema(
        request=serializers.AddRecipeSerializer, responses=serializers.ShoppingListSerializer
    )
    @action(detail=True, methods=["post"], url_path="add-recipe")
    def add_recipe(self, request, pk=None):
        shopping_list = self.get_object()
        payload = serializers.AddRecipeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        shopping.add_recipe(shopping_list, **payload.validated_data)
        return Response(self.get_serializer(self.get_object()).data)


class ShoppingItemViewSet(
    OwnedMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet
):
    serializer_class = serializers.ShoppingItemSerializer
    model = ShoppingItem

    def owned(self, queryset):
        return queryset.filter(shopping_list__user=self.request.user)


class ProductViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    lookup_value_regex = r"\d{8,14}"

    @extend_schema(responses=serializers.ProductSerializer)
    def retrieve(self, request, pk=None):
        try:
            product = openfoodfacts.get_product(pk)
        except ServiceError as exc:
            raise NotFound("Open Food Facts est indisponible.") from exc
        if product is None:
            raise NotFound("Produit introuvable.")
        return Response(serializers.ProductSerializer(product).data)
