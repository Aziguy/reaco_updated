from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("", views.pricing, name="pricing"),
    path("choisir/<slug:slug>/", views.checkout, name="checkout"),
    path("paiement/<str:reference>/", views.payment, name="payment"),
    path("paiement/<str:reference>/effectue/", views.declare, name="declare"),
    path("paiement/<str:reference>/annuler/", views.withdraw, name="withdraw"),
    path("mon-abonnement/", views.account, name="account"),
    path("gerer/", views.portal, name="portal"),
    path("stripe/webhook/", views.webhook, name="webhook"),
    path("ou-va-votre-argent/", views.costs, name="costs"),
]
