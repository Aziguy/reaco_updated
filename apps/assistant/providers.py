"""Model clients behind one call: system prompt, user prompt and JSON schema in, dict out."""

import base64
import json
import re
from dataclasses import dataclass, field

import anthropic
import httpx
from django.conf import settings

from .models import AIModel, Provider

# Server-side refusal fallback (Claude API), available on these models only.
SERVER_FALLBACK_MODELS = {"claude-opus-5-5", "claude-sonnet-5-5", "claude-fable-5-1"}
SERVER_FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AIError(Exception):
    pass


@dataclass
class Prompt:
    system: str
    text: str
    schema: dict
    effort: str = ""
    max_tokens: int = 4000
    images: list[tuple[str, bytes]] = field(default_factory=list)


@dataclass
class Completion:
    data: dict
    input_tokens: int = 0
    output_tokens: int = 0


def parse_json(text: str) -> dict:
    """JSON object from a reply, tolerating code fences or surrounding prose."""
    match = re.search(r"\{.*\}", text or "", re.DOTALL)
    try:
        data = json.loads(match.group(0) if match else text)
    except (TypeError, ValueError) as exc:
        raise AIError("Réponse illisible") from exc
    if not isinstance(data, dict):
        raise AIError("Réponse inattendue")
    return data


class AnthropicClient:
    def __init__(self, model: AIModel):
        self.model = model
        self.client = anthropic.Anthropic(
            api_key=model.provider.api_key,
            base_url=model.provider.base_url or None,
            timeout=settings.AI["TIMEOUT"],
            max_retries=1,
        )

    def complete(self, prompt: Prompt) -> Completion:
        content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": base64.standard_b64encode(data).decode(),
                },
            }
            for media_type, data in prompt.images
        ]
        content.append({"type": "text", "text": prompt.text})
        output_config = {"format": {"type": "json_schema", "schema": prompt.schema}}
        if prompt.effort and self.model.supports_effort:
            output_config["effort"] = prompt.effort
        params = {
            "model": self.model.model_id,
            "max_tokens": prompt.max_tokens,
            "system": prompt.system,
            "messages": [{"role": "user", "content": content}],
            "output_config": output_config,
        }
        try:
            if self.model.model_id in SERVER_FALLBACK_MODELS:
                response = self.client.beta.messages.create(
                    betas=[SERVER_FALLBACK_BETA], fallbacks="default", **params
                )
            else:
                response = self.client.messages.create(**params)
        except anthropic.APIError as exc:
            raise AIError(f"{type(exc).__name__}: {exc}"[:300]) from exc
        if response.stop_reason == "refusal":
            raise AIError("Demande refusée par le modèle")
        if response.stop_reason == "max_tokens":
            raise AIError("Réponse tronquée : augmentez les jetons de sortie de la route")
        text = next((block.text for block in response.content if block.type == "text"), "")
        return Completion(
            parse_json(text), response.usage.input_tokens, response.usage.output_tokens
        )


class OpenAICompatibleClient:
    """Chat Completions API, shared by GitHub Models, Mistral, Ollama, Groq and OpenRouter."""

    def __init__(self, model: AIModel):
        self.model = model

    def complete(self, prompt: Prompt) -> Completion:
        content: list[dict] = [{"type": "text", "text": prompt.text}]
        for media_type, data in prompt.images:
            url = f"data:{media_type};base64,{base64.standard_b64encode(data).decode()}"
            content.append({"type": "image_url", "image_url": {"url": url}})
        payload = {
            "model": self.model.model_id,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": content if prompt.images else prompt.text},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "answer", "schema": prompt.schema, "strict": True},
            },
        }
        if self.model.supports_effort:
            payload["max_completion_tokens"] = prompt.max_tokens
            if prompt.effort:
                payload["reasoning_effort"] = prompt.effort
        else:
            payload["max_tokens"] = prompt.max_tokens
        provider = self.model.provider
        headers = {"Authorization": f"Bearer {provider.api_key}"} if provider.api_key else {}
        try:
            response = httpx.post(
                f"{provider.base_url.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=settings.AI["TIMEOUT"],
            )
            response.raise_for_status()
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise AIError(f"HTTP {exc.response.status_code}: {exc.response.text}"[:300]) from exc
        except (httpx.HTTPError, ValueError, KeyError, IndexError) as exc:
            raise AIError(f"{type(exc).__name__}: {exc}"[:300]) from exc
        usage = body.get("usage") or {}
        return Completion(
            parse_json(text), usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
        )


CLIENTS = {
    Provider.Kind.ANTHROPIC: AnthropicClient,
    Provider.Kind.OPENAI: OpenAICompatibleClient,
}


def client_for(model: AIModel):
    return CLIENTS[model.provider.kind](model)
