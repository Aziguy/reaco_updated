from django.urls import path

from . import views

app_name = "shopping"

urlpatterns = [
    path("", views.index, name="index"),
    path("ajouter-recette/", views.add_recipe, name="add_recipe"),
    path("<int:pk>/", views.detail, name="detail"),
    path("<int:pk>/articles/", views.add_item, name="add_item"),
    path("<int:pk>/comparer/", views.compare, name="compare"),
    path("<int:pk>/imprimer/", views.print_view, name="print"),
    path("<int:pk>/ranger/", views.checkout, name="checkout"),
    path("<int:pk>/archiver/", views.archive, name="archive"),
    path("<int:pk>/supprimer/", views.delete, name="delete"),
    path("articles/<int:pk>/cocher/", views.toggle_item, name="toggle_item"),
    path("articles/<int:pk>/supprimer/", views.delete_item, name="delete_item"),
]
