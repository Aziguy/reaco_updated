from django.urls import path

from . import views

app_name = "assistant"

urlpatterns = [
    path("recherche/", views.search, name="search"),
]
