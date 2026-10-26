import unicodedata

from django.utils.text import slugify

LIGATURES = str.maketrans({"œ": "oe", "Œ": "Oe", "æ": "ae", "Æ": "Ae"})


def make_slug(value: str) -> str:
    return slugify(value.translate(LIGATURES))


def normalize(value: str) -> str:
    """Lowercase text without accents, for accent-insensitive search."""
    decomposed = unicodedata.normalize("NFKD", value.translate(LIGATURES).lower())
    return " ".join("".join(c for c in decomposed if not unicodedata.combining(c)).split())
