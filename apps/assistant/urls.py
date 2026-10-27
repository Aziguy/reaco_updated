from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("", views.hub, name="hub"),
    path("recherche/", views.search, name="search"),
    path("menu/", views.plan_new, name="plan_new"),
    path("menu/<int:pk>/", views.plan_detail, name="plan"),
    path("menu/<int:pk>/preparer/", views.plan_run, name="plan_run"),
    path("menu/<int:pk>/courses/", views.plan_shopping, name="plan_shopping"),
    path("menu/<int:pk>/repas/<int:meal_pk>/changer/", views.meal_swap, name="meal_swap"),
    path("frigo/", views.fridge, name="fridge"),
    path("recette/<slug:slug>/proposer/", views.propose, name="propose"),
    path("ticket/", views.receipt, name="receipt"),
    path("ticket/ajouter/", views.receipt_save, name="receipt_save"),
]
