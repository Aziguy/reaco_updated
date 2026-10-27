import pytest

from apps.assistant import services
from apps.assistant.models import AIModel, Feature, Mode, Provider, Route
from apps.assistant.providers import AIError, Completion


class FakeClient:
    def __init__(self, replies, prompts):
        self.replies = replies
        self.prompts = prompts

    def complete(self, prompt):
        self.prompts.append(prompt)
        reply = self.replies.pop(0) if self.replies else {}
        if isinstance(reply, Exception):
            raise reply
        return Completion(reply, input_tokens=1000, output_tokens=200)


class FakeAI:
    """Queue replies (dicts or AIError) answered by any model, and record prompts."""

    def __init__(self):
        self.replies: list = []
        self.prompts: list = []
        self.models: list = []

    def reply(self, *replies):
        self.replies.extend(replies)

    def fail(self, message="boom"):
        self.replies.append(AIError(message))


@pytest.fixture
def ai_config(db, monkeypatch):
    monkeypatch.setenv("TEST_AI_KEY", "test")
    provider = Provider.objects.create(
        name="Test", kind=Provider.Kind.ANTHROPIC, api_key_env="TEST_AI_KEY"
    )
    main = AIModel.objects.create(
        provider=provider, model_id="main", label="Main", supports_vision=True,
        supports_effort=True, input_price=1, output_price=5,
    )  # fmt: skip
    backup = AIModel.objects.create(provider=provider, model_id="backup", label="Backup")
    for feature in Feature.values:
        for mode in Mode.values:
            Route.objects.create(
                feature=feature, mode=mode, model=main, fallback=backup,
                daily_quota=5, anonymous_quota=2 if feature == Feature.SEARCH else 0,
            )  # fmt: skip
    return {"main": main, "backup": backup}


@pytest.fixture
def fake_ai(ai_config, monkeypatch):
    fake = FakeAI()

    def client_for(model):
        fake.models.append(model.model_id)
        return FakeClient(fake.replies, fake.prompts)

    monkeypatch.setattr(services, "client_for", client_for)
    return fake
