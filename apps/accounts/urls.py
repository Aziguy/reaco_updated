from django.urls import path

from . import views

app_name = "accounts"

urlpatterns = [
    path("profil/", views.profile, name="profile"),
    path("supprimer/", views.delete_account, name="delete"),
]
