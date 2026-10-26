from django.urls import path

from . import views

app_name = "recipes"

urlpatterns = [
    path("", views.recipe_list, name="list"),
    path("favoris/", views.favorites, name="favorites"),
    path("<slug:slug>/", views.recipe_detail, name="detail"),
    path("<slug:slug>/prix/", views.recipe_prices, name="prices"),
    path("<slug:slug>/favori/", views.toggle_favorite, name="favorite"),
]
