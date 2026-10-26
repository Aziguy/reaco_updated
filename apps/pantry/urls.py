from django.urls import path

from . import views

app_name = "pantry"

urlpatterns = [
    path("garde-manger/", views.pantry_list, name="list"),
    path("garde-manger/ajouter/", views.pantry_form, name="add"),
    path("garde-manger/scan/", views.pantry_lookup, name="lookup"),
    path("garde-manger/stats/", views.pantry_stats, name="stats"),
    path("garde-manger/<int:pk>/modifier/", views.pantry_form, name="edit"),
    path("garde-manger/<int:pk>/supprimer/", views.pantry_delete, name="delete"),
    path("garde-manger/<int:pk>/<str:status>/", views.pantry_close, name="close"),
    path("anti-gaspi/", views.suggestions, name="suggestions"),
]
