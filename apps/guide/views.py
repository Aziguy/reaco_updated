from django.http import Http404
from django.shortcuts import render

from .content import CHAPTERS, CHAPTERS_BY_SLUG


def index(request):
    return render(request, "guide/index.html", {"chapters": CHAPTERS})


def chapter(request, slug):
    current = CHAPTERS_BY_SLUG.get(slug)
    if current is None:
        raise Http404
    position = CHAPTERS.index(current)
    context = {
        "chapters": CHAPTERS,
        "chapter": current,
        "previous": CHAPTERS[position - 1] if position else None,
        "next": CHAPTERS[position + 1] if position + 1 < len(CHAPTERS) else None,
    }
    return render(request, "guide/chapter.html", context)
