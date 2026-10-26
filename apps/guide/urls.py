from django.urls import path

from . import views

app_name = "guide"

urlpatterns = [
    path("", views.index, name="index"),
    path("<slug:slug>/", views.chapter, name="chapter"),
]
