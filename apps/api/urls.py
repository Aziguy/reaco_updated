from csp.constants import UNSAFE_INLINE
from csp.decorators import csp_update
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerSplitView
from rest_framework.routers import DefaultRouter

from . import views

app_name = "api"

router = DefaultRouter()
router.register("recipes", views.RecipeViewSet, basename="recipe")
router.register("ingredients", views.IngredientViewSet, basename="ingredient")
router.register("pantry", views.PantryItemViewSet, basename="pantry")
router.register("shopping-lists", views.ShoppingListViewSet, basename="shopping-list")
router.register("shopping-items", views.ShoppingItemViewSet, basename="shopping-item")
router.register("products", views.ProductViewSet, basename="product")

urlpatterns = [
    path("v1/", include(router.urls)),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "docs/",
        csp_update({"style-src": [UNSAFE_INLINE]})(
            SpectacularSwaggerSplitView.as_view(url_name="api:schema")
        ),
        name="docs",
    ),
]
