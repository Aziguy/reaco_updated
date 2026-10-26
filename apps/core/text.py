from django.utils.text import slugify

LIGATURES = str.maketrans({"œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae"})


def make_slug(value: str) -> str:
    return slugify(value.translate(LIGATURES))
