from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("tableau-de-bord/", views.dashboard, name="dashboard"),
    path("saison/", views.season, name="season"),
    path("a-propos/", views.about, name="about"),
    path("contact/", views.contact, name="contact"),
    path("health/", views.health, name="health"),
]
