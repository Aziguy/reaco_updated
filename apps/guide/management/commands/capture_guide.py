import io
import json
import secrets
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import httpx
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db.models import F
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFont

from apps.assistant import planner
from apps.assistant.generator import GenerationError, create_recipe
from apps.assistant.models import MealPlan
from apps.assistant.services import Caller, Unavailable
from apps.billing.models import Plan, Subscription
from apps.guide.content import FIGURES, Figure
from apps.pantry.models import PantryItem
from apps.recipes.models import Favorite, Ingredient, Recipe
from apps.shopping.models import ShoppingItem, ShoppingList
from apps.shopping.services import add_recipe

EMAIL = "guide@comegusto.local"
OUTPUT = settings.BASE_DIR / "static" / "img" / "guide"
THEMES = ("light", "dark")
PADDING = 32

PANTRY = [
    # slug, name, quantity, unit, days before expiry (None: no date), value
    ("tomate", "Tomates grappe", 1, "kg", 1, "3.20"),
    ("courgette", "Courgettes", 2, "piece", 2, "1.80"),
    ("lait-demi-ecreme", "Lait demi-écrémé", 1, "l", 0, "1.05"),
    ("oeuf", "Œufs plein air", 6, "piece", 9, "2.40"),
    ("pomme", "Pommes Gala", 4, "piece", -1, "2.10"),
    ("oignon", "Oignons jaunes", 1, "kg", None, "1.60"),
    ("pates", "Pâtes penne", 500, "g", 240, "0.95"),
    ("riz", "Riz basmati", 1, "kg", 300, "2.30"),
    ("yaourt-grec", "Yaourt à la grecque", 500, "g", 6, "2.60"),
]
CLOSED = [
    ("Carottes", PantryItem.Status.CONSUMED, 3, "1.20"),
    ("Pain de mie", PantryItem.Status.CONSUMED, 6, "1.50"),
    ("Salade", PantryItem.Status.WASTED, 9, "1.10"),
]
RECEIPT = [
    "      MARCHÉ DU QUARTIER",
    "    12 rue des Lilas, Paris",
    "",
    "TOMATES GRAPPE 0,812 KG   2,43",
    "COURGETTES BIO X2         1,98",
    "OEUFS PLEIN AIR X6        2,35",
    "LAIT DEMI-ECREME 1L       1,05",
    "PATES PENNE 500G          0,95",
    "SAC CABAS                 0,10",
    "OIGNONS JAUNES 1KG        1,60",
    "",
    "TOTAL                    10,46",
]
FAVORITES = ["ratatouille", "dahl-de-lentilles-corail", "crepes"]

OVERLAY = """
([boxes, dark]) => {
  const color = "#ea580c";
  const halo = dark ? "rgba(12, 10, 9, 0.9)" : "rgba(255, 255, 255, 0.95)";
  const root = document.createElement("div");
  Object.assign(root.style, {position: "absolute", left: "0", top: "0", zIndex: "2147483647",
    pointerEvents: "none"});
  boxes.forEach(([x, y, w, h], index) => {
    const pad = 6;
    const ring = document.createElement("div");
    Object.assign(ring.style, {position: "absolute", left: `${x - pad}px`, top: `${y - pad}px`,
      width: `${w + 2 * pad}px`, height: `${h + 2 * pad}px`, border: `3px solid ${color}`,
      borderRadius: "14px", boxShadow: `0 0 0 3px ${halo}`, boxSizing: "border-box"});
    const badge = document.createElement("div");
    badge.textContent = String(index + 1);
    Object.assign(badge.style, {position: "absolute", left: `${Math.max(4, x - pad - 14)}px`,
      top: `${Math.max(4, y - pad - 14)}px`, width: "28px", height: "28px", borderRadius: "50%",
      background: color, color: "#fff", font: "700 15px/28px system-ui, sans-serif",
      textAlign: "center", boxShadow: `0 0 0 3px ${halo}, 0 2px 6px rgba(0, 0, 0, 0.35)`});
    root.append(ring, badge);
  });
  document.body.append(root);
}
"""
BOX = "el => { const r = el.getBoundingClientRect(); return [r.left + scrollX, r.top + scrollY, r.width, r.height]; }"  # noqa: E501


class Command(BaseCommand):
    help = "Capture les figures annotées du guide utilisateur (serveur de développement requis)."

    def add_arguments(self, parser):
        parser.add_argument("names", nargs="*", help="Figures à capturer (toutes par défaut).")
        parser.add_argument("--base-url", default="http://127.0.0.1:8000")

    def handle(self, *args, names, base_url, **options):
        from playwright.sync_api import sync_playwright

        unknown = set(names) - set(FIGURES)
        if unknown:
            raise CommandError(f"Figures inconnues : {', '.join(sorted(unknown))}")
        base_url = base_url.rstrip("/")
        try:
            httpx.get(f"{base_url}/health/", timeout=5).raise_for_status()
        except httpx.HTTPError as exc:
            raise CommandError(f"Serveur injoignable sur {base_url} : lancez runserver.") from exc

        password = secrets.token_urlsafe(16)
        figures = [FIGURES[name] for name in names] if names else list(FIGURES.values())
        paths = self.prepare_account(password)
        paths.update(self.prepare_assistant(figures, Path(tempfile.mkdtemp())))
        OUTPUT.mkdir(parents=True, exist_ok=True)
        manifest_path = OUTPUT / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            state = self.login(browser, base_url, password)
            for figure in figures:
                for theme in THEMES:
                    image = self.capture(browser, base_url, figure, theme, state, paths)
                    image.save(OUTPUT / f"{figure.name}-{theme}.webp", quality=82, method=6)
                manifest[figure.name] = {"width": image.width, "height": image.height}
                self.stdout.write(f"{figure.name} ({image.width}x{image.height})")
            browser.close()

        manifest_path.write_text(json.dumps(dict(sorted(manifest.items())), indent=2) + "\n")
        self.stdout.write(self.style.SUCCESS(f"{len(figures)} figure(s) dans {OUTPUT}"))

    def prepare_account(self, password: str) -> dict:
        user, _ = get_user_model().objects.get_or_create(email=EMAIL)
        user.first_name = "Camille"
        user.postal_code, user.city = "75011", "Paris"
        user.latitude, user.longitude = 48.8590, 2.3790
        user.household_size = 4
        user.expiry_reminders = True
        user.set_password(password)
        user.save()

        user.pantry_items.all().delete()
        user.shopping_lists.all().delete()
        user.subscriptions.all().delete()
        user.authenticator_set.all().delete()
        plan = Plan.objects.filter(slug="plus").first()
        if plan:
            Subscription.objects.create(
                user=user, plan=plan, method=Subscription.Method.TRANSFER, amount=plan.yearly_price,
                period="year", status=Subscription.Status.ACTIVE, starts_on=timezone.localdate(),
                ends_on=timezone.localdate() + timedelta(days=200),
            )  # fmt: skip
        Favorite.objects.filter(user=user).delete()

        today = timezone.localdate()
        ingredients = Ingredient.objects.in_bulk([row[0] for row in PANTRY], field_name="slug")
        for slug, name, quantity, unit, days, value in PANTRY:
            PantryItem.objects.create(
                user=user,
                ingredient=ingredients.get(slug),
                name=name,
                quantity=quantity,
                unit=unit,
                expires_on=None if days is None else today + timedelta(days=days),
                estimated_value=Decimal(value),
            )
        for name, status, days_ago, value in CLOSED:
            PantryItem.objects.create(
                user=user,
                name=name,
                status=status,
                closed_on=today - timedelta(days=days_ago),
                estimated_value=Decimal(value),
            )
        for recipe in Recipe.objects.filter(slug__in=FAVORITES):
            Favorite.objects.create(user=user, recipe=recipe)

        shopping_list = ShoppingList.objects.create(user=user, name="Courses de la semaine")
        for slug in ("couscous", "crepes"):
            recipe = Recipe.objects.filter(slug=slug).first()
            if recipe:
                add_recipe(shopping_list, recipe, 4)
        ShoppingItem.objects.create(shopping_list=shopping_list, label="Pain de campagne")
        first = shopping_list.items.order_by("pk").first()
        if first:
            first.is_checked = True
            first.save(update_fields=["is_checked"])
        return {"shopping_list": shopping_list.get_absolute_url()}

    def prepare_assistant(self, figures: list[Figure], folder: Path) -> dict:
        """Real assistant answers for the figures that show them (a few cents at most)."""
        used = " ".join(figure.path for figure in figures)
        used += " ".join(
            arg for figure in figures for _, _, *args in figure.actions for arg in args
        )
        user = get_user_model().objects.get(email=EMAIL)
        caller = Caller(user, "127.0.0.1")
        paths = {}
        try:
            if "{plan}" in used:
                user.meal_plans.all().delete()
                plan = MealPlan.objects.create(
                    user=user, days=5, servings=4, budget=Decimal(60),
                    preferences="un plat de pâtes, pas trop épicé",
                )  # fmt: skip
                paths["plan"] = planner.generate(plan, caller).get_absolute_url()
            if "{ai_recipe}" in used:
                Recipe.objects.filter(author=user, is_ai_generated=True).delete()
                products = user.pantry_items.in_stock().order_by(
                    F("expires_on").asc(nulls_last=True)
                )
                recipe = create_recipe(list(products[:4]), 4, "sans four", "fast", caller)
                paths["ai_recipe"] = recipe.get_absolute_url()
        except (Unavailable, GenerationError) as exc:
            raise CommandError(f"Assistant indisponible : {exc}") from exc
        if "{receipt}" in used:
            paths["receipt"] = str(self.receipt_image(folder / "ticket.jpg"))
        return paths

    def receipt_image(self, path: Path) -> Path:
        image = Image.new("RGB", (620, 900), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default(size=22)
        for index, line in enumerate(RECEIPT):
            draw.text((30, 40 + index * 44), line, fill="black", font=font)
        image.save(path, "JPEG", quality=90)
        return path

    def context(self, browser, figure: Figure, theme: str, state=None):
        context = browser.new_context(
            viewport={"width": figure.width, "height": figure.height},
            device_scale_factor=2 if figure.mobile else 1,
            is_mobile=figure.mobile,
            has_touch=figure.mobile,
            color_scheme=theme,
            reduced_motion="reduce",
            locale="fr-FR",
            bypass_csp=True,
            storage_state=state,
        )
        context.add_init_script(f"localStorage.setItem('theme', '{theme}')")
        return context

    def login(self, browser, base_url: str, password: str) -> dict:
        context = self.context(browser, next(iter(FIGURES.values())), "light")
        page = context.new_page()
        page.goto(f"{base_url}/compte/login/")
        page.fill("#id_login", EMAIL)
        page.fill("#id_password", password)
        page.click('main form button[type="submit"]')
        page.wait_for_url(lambda url: "/compte/login/" not in url)
        state = context.storage_state()
        context.close()
        return state

    def capture(self, browser, base_url, figure: Figure, theme, state, paths) -> Image.Image:
        context = self.context(browser, figure, theme, state if figure.auth else None)
        page = context.new_page()
        page.goto(base_url + figure.path.format(**paths), wait_until="networkidle")
        for action, selector, *args in figure.actions:
            getattr(page.locator(selector).first, action)(*(a.format(**paths) for a in args))
        page.wait_for_load_state("networkidle")
        if figure.wait_for:
            page.wait_for_selector(figure.wait_for)
        page.evaluate("scrollTo(0, 0)")
        page.wait_for_timeout(400)

        boxes = []
        for callout in figure.callouts:
            locator = page.locator(callout.selector).first
            try:
                locator.wait_for(state="visible", timeout=5000)
            except Exception as exc:
                raise CommandError(
                    f"{figure.name} : élément introuvable {callout.selector}"
                ) from exc
            boxes.append(locator.evaluate(BOX))
        region = None
        if figure.clip:
            boxes_in = [page.locator(figure.clip).first.evaluate(BOX), *boxes]
            left = max(0, min(b[0] for b in boxes_in) - PADDING)
            top = max(0, min(b[1] for b in boxes_in) - PADDING)
            right = min(figure.width, max(b[0] + b[2] for b in boxes_in) + PADDING)
            bottom = max(b[1] + b[3] for b in boxes_in) + PADDING
            region = {"x": left, "y": top, "width": right - left, "height": bottom - top}

        page.evaluate(OVERLAY, [boxes, theme == "dark"])
        png = page.screenshot(full_page=bool(region), clip=region, animations="disabled")
        context.close()
        return Image.open(io.BytesIO(png)).convert("RGB")
