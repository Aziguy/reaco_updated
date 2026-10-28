import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_dashboard_shows_key_figures(admin_client, recipe):
    content = admin_client.get(reverse("admin:index")).content.decode()
    for text in ("Recettes publiées", "Budget de l", "Recettes à relire"):
        assert text in content


@pytest.mark.parametrize(
    "name",
    [
        "recipes_recipe_changelist",
        "assistant_usage_changelist",
        "accounts_user_changelist",
        "account_emailaddress_changelist",
        "authtoken_tokenproxy_changelist",
    ],
)
def test_admin_pages_render(admin_client, recipe, name):
    assert admin_client.get(reverse(f"admin:{name}")).status_code == 200


def test_recipe_form_uses_tabs(admin_client, recipe):
    response = admin_client.get(reverse("admin:recipes_recipe_change", args=[recipe.pk]))
    assert response.status_code == 200
    assert "Chiffres calculés" in response.content.decode()


def test_csp_is_only_relaxed_for_the_admin(admin_client):
    admin_policy = admin_client.get(reverse("admin:index"))["Content-Security-Policy"]
    site_policy = admin_client.get(reverse("core:home"))["Content-Security-Policy"]
    assert "'unsafe-eval'" in admin_policy and "'unsafe-inline'" in admin_policy
    assert "unsafe" not in site_policy
