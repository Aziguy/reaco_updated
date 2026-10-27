import json
from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest
from django.core.management import call_command

from apps.assistant import providers
from apps.assistant.models import AIModel, Feature, Mode, Provider, Route, Usage
from apps.assistant.providers import AIError, Prompt, parse_json
from apps.assistant.services import Caller, Unavailable, ask, availability

pytestmark = pytest.mark.django_db

PROMPT = Prompt(system="s", text="t", schema={"type": "object"})


def caller(user=None):
    return Caller(user, "1.2.3.4")


def test_ask_records_usage_and_cost(fake_ai, user):
    fake_ai.reply({"ok": True})
    assert ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT) == {"ok": True}
    usage = Usage.objects.get()
    assert usage.ok and usage.user == user
    assert usage.cost == Decimal("0.002")  # 1000 x 1 $ + 200 x 5 $ per million


def test_ask_uses_route_effort_and_tokens(fake_ai, user):
    Route.objects.filter(feature=Feature.SEARCH).update(effort="medium", max_tokens=1234)
    fake_ai.reply({})
    ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT)
    assert (fake_ai.prompts[0].effort, fake_ai.prompts[0].max_tokens) == ("medium", 1234)


def test_ask_falls_back_to_second_model(fake_ai, user):
    fake_ai.fail()
    fake_ai.reply({"from": "backup"})
    assert ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT) == {"from": "backup"}
    assert fake_ai.models == ["main", "backup"]
    assert list(Usage.objects.order_by("pk").values_list("ok", flat=True)) == [False, True]


def test_ask_unavailable_when_every_model_fails(fake_ai, user):
    fake_ai.fail()
    fake_ai.fail()
    with pytest.raises(Unavailable) as exc:
        ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT)
    assert exc.value.reason == "error"


def test_images_skip_models_without_vision(fake_ai, user):
    fake_ai.fail()
    prompt = Prompt(system="s", text="t", schema={}, images=[("image/jpeg", b"x")])
    with pytest.raises(Unavailable):
        ask(Feature.RECEIPT, Mode.FAST, caller(user), prompt)
    assert fake_ai.models == ["main"]


def test_user_quota(fake_ai, user):
    fake_ai.reply(*[{}] * 5)
    for _ in range(5):
        ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT)
    with pytest.raises(Unavailable) as exc:
        ask(Feature.SEARCH, Mode.FAST, caller(user), PROMPT)
    assert exc.value.reason == "quota"


def test_visitor_quota_and_login_only_features(fake_ai):
    fake_ai.reply({}, {})
    ask(Feature.SEARCH, Mode.FAST, caller(), PROMPT)
    ask(Feature.SEARCH, Mode.FAST, caller(), PROMPT)
    with pytest.raises(Unavailable, match="limite"):
        ask(Feature.SEARCH, Mode.FAST, caller(), PROMPT)
    with pytest.raises(Unavailable) as exc:
        availability(Feature.PLANNER, Mode.FAST, caller())
    assert exc.value.reason == "login"


def test_monthly_budget_stops_the_assistant(fake_ai, user, settings):
    settings.AI = {**settings.AI, "MONTHLY_BUDGET_USD": 0.001}
    Usage.objects.create(feature=Feature.SEARCH, mode=Mode.FAST, cost=Decimal("0.002"))
    with pytest.raises(Unavailable) as exc:
        availability(Feature.SEARCH, Mode.FAST, caller(user))
    assert exc.value.reason == "budget"


def test_missing_key_or_disabled(ai_config, monkeypatch, settings, user):
    monkeypatch.delenv("TEST_AI_KEY")
    with pytest.raises(Unavailable, match="indisponible"):
        availability(Feature.SEARCH, Mode.FAST, caller(user))
    settings.AI = {**settings.AI, "ENABLED": False}
    with pytest.raises(Unavailable, match="indisponible"):
        availability(Feature.SEARCH, Mode.FAST, caller(user))


def test_deep_mode_falls_back_to_fast_route(fake_ai, user):
    Route.objects.filter(mode=Mode.DEEP, feature=Feature.SEARCH).delete()
    assert availability(Feature.SEARCH, Mode.DEEP, caller(user)).mode == Mode.FAST


@pytest.mark.parametrize(
    "text",
    ['{"a": 1}', '```json\n{"a": 1}\n```', 'Voici : {"a": 1} !'],
)
def test_parse_json_tolerates_wrapping(text):
    assert parse_json(text) == {"a": 1}


def test_parse_json_rejects_garbage():
    with pytest.raises(AIError):
        parse_json("pas de json")


def _openai_model(**extra):
    provider = Provider.objects.create(
        name="Compat", kind=Provider.Kind.OPENAI, base_url="https://llm.test/v1",
        api_key_env="COMPAT_KEY",
    )  # fmt: skip
    return AIModel.objects.create(provider=provider, model_id="m", label="M", **extra)


def test_openai_compatible_client(http, monkeypatch):
    monkeypatch.setenv("COMPAT_KEY", "secret")
    route = http.post("https://llm.test/v1/chat/completions").respond(
        json={
            "choices": [{"message": {"content": '{"answer": 42}'}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 3},
        }
    )
    completion = providers.client_for(_openai_model()).complete(PROMPT)
    assert (completion.data, completion.input_tokens, completion.output_tokens) == (
        {"answer": 42}, 10, 3,
    )  # fmt: skip
    request = route.calls.last.request
    body = json.loads(request.content)
    assert request.headers["Authorization"] == "Bearer secret"
    assert body["response_format"]["type"] == "json_schema"
    assert body["max_tokens"] == PROMPT.max_tokens and "reasoning_effort" not in body


def test_openai_compatible_reasoning_models(http):
    route = http.post("https://llm.test/v1/chat/completions").respond(
        json={"choices": [{"message": {"content": "{}"}}]}
    )
    prompt = Prompt(system="s", text="t", schema={}, effort="low")
    providers.client_for(_openai_model(supports_effort=True)).complete(prompt)
    body = json.loads(route.calls.last.request.content)
    assert body["reasoning_effort"] == "low" and "max_completion_tokens" in body


def test_openai_compatible_errors(http):
    client = providers.client_for(_openai_model())
    http.post("https://llm.test/v1/chat/completions").respond(429, text="slow down")
    with pytest.raises(AIError, match="429"):
        client.complete(PROMPT)
    http.post("https://llm.test/v1/chat/completions").mock(side_effect=httpx.ConnectError("x"))
    with pytest.raises(AIError):
        client.complete(PROMPT)


def _anthropic(model_id, monkeypatch, stop_reason="end_turn"):
    monkeypatch.setenv("ANTHROPIC_TEST_KEY", "k")
    provider = Provider.objects.create(
        name="A", kind=Provider.Kind.ANTHROPIC, api_key_env="ANTHROPIC_TEST_KEY"
    )
    model = AIModel.objects.create(
        provider=provider, model_id=model_id, label="A", supports_effort=True
    )
    client = providers.client_for(model)
    calls = []
    response = SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking"), SimpleNamespace(type="text", text='{"x": 1}')],
        usage=SimpleNamespace(input_tokens=5, output_tokens=2),
    )

    def create(**params):
        calls.append(params)
        return response

    monkeypatch.setattr(client.client.messages, "create", create)
    monkeypatch.setattr(client.client.beta.messages, "create", create)
    return client, calls


def test_anthropic_client_structured_output(monkeypatch):
    client, calls = _anthropic("claude-haiku-5-5", monkeypatch)
    prompt = Prompt(system="s", text="t", schema={"type": "object"}, effort="low")
    assert client.complete(prompt).data == {"x": 1}
    schema = {"type": "json_schema", "schema": {"type": "object"}}
    assert calls[0]["output_config"] == {"format": schema, "effort": "low"}
    assert "fallbacks" not in calls[0]


def test_anthropic_server_fallback_on_supported_models(monkeypatch):
    client, calls = _anthropic("claude-sonnet-5-5", monkeypatch)
    client.complete(PROMPT)
    assert calls[0]["fallbacks"] == "default"
    assert calls[0]["betas"] == [providers.SERVER_FALLBACK_BETA]


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_anthropic_incomplete_replies(monkeypatch, stop_reason):
    client, _ = _anthropic("claude-haiku-5-5", monkeypatch, stop_reason)
    with pytest.raises(AIError):
        client.complete(PROMPT)


def test_setup_assistant_is_idempotent(db):
    call_command("setup_assistant")
    call_command("setup_assistant")
    assert Route.objects.count() == len(Feature.values) * len(Mode.values)
    assert Provider.objects.get(name="Anthropic").api_key_env == "ANTHROPIC_API_KEY"
