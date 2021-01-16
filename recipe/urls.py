from django.urls import path
from . import views

urlpatterns = [
    path('', views.recipe, name='recipe'),
    path('<int:id>', views.recipe_details, name='recipe_details'),
    path('search', views.search, name='search'),
]