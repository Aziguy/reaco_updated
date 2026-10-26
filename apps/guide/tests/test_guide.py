import json

import pytest
from django.conf import settings
from django.urls import reverse

from apps.guide.content import CHAPTERS, FIGURES

pytestmark = pytest.mark.django_db

GUIDE_IMAGES = settings.BASE_DIR / "static" / "img" / "guide"


def test_index_lists_every_chapter(client):
    content = client.get(reverse("guide:index")).content.decode()
    for chapter in CHAPTERS:
        assert reverse("guide:chapter", args=[chapter.slug]) in content


@pytest.mark.parametrize("chapter", CHAPTERS, ids=lambda chapter: chapter.slug)
def test_chapter_renders_its_figures(client, chapter):
    response = client.get(reverse("guide:chapter", args=[chapter.slug]))
    assert response.status_code == 200
    content = response.content.decode()
    for name in chapter.figures:
        assert f"img/guide/{name}-light.webp" in content
        assert f"img/guide/{name}-dark.webp" in content
        for callout in FIGURES[name].callouts:
            assert callout.title.replace("'", "&#x27;") in content


def test_unknown_chapter_is_404(client):
    assert client.get(reverse("guide:chapter", args=["inconnu"])).status_code == 404


def test_every_figure_belongs_to_one_chapter():
    used = [name for chapter in CHAPTERS for name in chapter.figures]
    assert sorted(used) == sorted(FIGURES)


def test_figure_images_are_captured():
    manifest = json.loads((GUIDE_IMAGES / "manifest.json").read_text())
    for name in FIGURES:
        assert manifest[name]["width"] > 0
        for theme in ("light", "dark"):
            assert (GUIDE_IMAGES / f"{name}-{theme}.webp").exists()


def test_guide_is_linked_from_every_page(client):
    assert reverse("guide:index") in client.get(reverse("core:home")).content.decode()
