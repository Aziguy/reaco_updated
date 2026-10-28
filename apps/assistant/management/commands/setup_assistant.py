from django.core.management.base import BaseCommand

from apps.assistant.models import AIModel, Effort, Feature, Mode, Provider, Route

PROVIDERS = [
    # name, kind, base_url, key variable, active
    ("Anthropic", Provider.Kind.ANTHROPIC, "", "ANTHROPIC_API_KEY", True),
    ("GitHub Models", Provider.Kind.OPENAI, "https://models.github.ai/inference",
     "GITHUB_MODELS_TOKEN", True),
    ("Mistral", Provider.Kind.OPENAI, "https://api.mistral.ai/v1", "MISTRAL_API_KEY", True),
    ("Ollama", Provider.Kind.OPENAI, "http://localhost:11434/v1", "", False),
]  # fmt: skip

MODELS = [
    # provider, model id, label, vision, effort, input $, output $
    ("Anthropic", "claude-haiku-5-5", "Claude Haiku 5.5", True, True, "0.10", "0.50"),
    ("Anthropic", "claude-sonnet-5-5", "Claude Sonnet 5.5", True, True, "2", "10"),
    ("Anthropic", "claude-opus-5-5", "Claude Opus 5.5", True, True, "4", "20"),
    ("GitHub Models", "openai/gpt-4.1-mini", "GPT-4.1 mini (GitHub)", True, False, "0", "0"),
    ("Mistral", "mistral-small-latest", "Mistral Small", True, False, "0.10", "0.30"),
    ("Ollama", "llama3.2", "Llama 3.2 (local)", False, False, "0", "0"),
]

HAIKU, SONNET, MISTRAL = "claude-haiku-5-5", "claude-sonnet-5-5", "mistral-small-latest"
ROUTES = [
    # feature, mode, model, fallback, effort, max tokens, user quota, visitor quota
    (Feature.SEARCH, Mode.FAST, HAIKU, MISTRAL, Effort.LOW, 4000, 60, 3),
    (Feature.SEARCH, Mode.DEEP, SONNET, HAIKU, Effort.LOW, 8000, 20, 0),
    (Feature.PLANNER, Mode.FAST, HAIKU, MISTRAL, Effort.LOW, 8000, 6, 0),
    (Feature.PLANNER, Mode.DEEP, SONNET, HAIKU, Effort.MEDIUM, 16000, 3, 0),
    (Feature.RECIPE, Mode.FAST, HAIKU, MISTRAL, Effort.LOW, 8000, 10, 0),
    (Feature.RECIPE, Mode.DEEP, SONNET, HAIKU, Effort.MEDIUM, 16000, 5, 0),
    (Feature.RECEIPT, Mode.FAST, HAIKU, MISTRAL, Effort.LOW, 8000, 10, 0),
    (Feature.RECEIPT, Mode.DEEP, SONNET, HAIKU, Effort.LOW, 12000, 5, 0),
    (Feature.PHOTO, Mode.FAST, HAIKU, MISTRAL, Effort.LOW, 4000, 10, 0),
    (Feature.PHOTO, Mode.DEEP, SONNET, HAIKU, Effort.LOW, 4000, 5, 0),
    (Feature.CATALOG, Mode.FAST, HAIKU, SONNET, Effort.LOW, 16000, 200, 0),
    (Feature.CATALOG, Mode.DEEP, SONNET, HAIKU, Effort.MEDIUM, 16000, 100, 0),
]


class Command(BaseCommand):
    help = "Crée les fournisseurs, modèles et routes par défaut de l'assistant (sans écraser)."

    def handle(self, *args, **options):
        providers = {}
        for name, kind, base_url, key_env, active in PROVIDERS:
            providers[name], _ = Provider.objects.get_or_create(
                name=name,
                defaults={
                    "kind": kind,
                    "base_url": base_url,
                    "api_key_env": key_env,
                    "is_active": active,
                },
            )
        models = {}
        for provider, model_id, label, vision, effort, input_price, output_price in MODELS:
            models[model_id], _ = AIModel.objects.get_or_create(
                provider=providers[provider],
                model_id=model_id,
                defaults={
                    "label": label,
                    "supports_vision": vision,
                    "supports_effort": effort,
                    "input_price": input_price,
                    "output_price": output_price,
                },
            )
        created = 0
        for feature, mode, model, fallback, effort, tokens, quota, visitors in ROUTES:
            _, new = Route.objects.get_or_create(
                feature=feature,
                mode=mode,
                defaults={
                    "model": models[model],
                    "fallback": models[fallback],
                    "effort": effort,
                    "max_tokens": tokens,
                    "daily_quota": quota,
                    "anonymous_quota": visitors,
                },
            )
            created += new
        configured = [p.name for p in providers.values() if p.is_active and p.is_configured]
        self.stdout.write(self.style.SUCCESS(f"{created} route(s) créée(s)."))
        ready = ", ".join(configured) or "aucun (clé manquante)"
        self.stdout.write(f"Fournisseurs prêts : {ready}")
