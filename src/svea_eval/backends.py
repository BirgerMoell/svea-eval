"""Generation backends for hosted APIs and local Transformers models."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from .models import Generation, Item


DEFAULT_SYSTEM_PROMPT = (
    "Du deltar i en utvärdering av svensk språkförmåga. Följ uppgiftens "
    "svarsinstruktion exakt. Använd bara underlaget när ett underlag ges."
)


@dataclass(frozen=True)
class GenerationConfig:
    temperature: float = 0.0
    seed: int | None = 17
    system_prompt: str = DEFAULT_SYSTEM_PROMPT


class Backend(ABC):
    name: str
    model_id: str

    @abstractmethod
    def generate(self, item: Item, config: GenerationConfig) -> Generation:
        """Generate one answer for an evaluation item."""


class OpenAICompatibleBackend(Backend):
    """Small dependency-free client for OpenAI-compatible chat endpoints."""

    name = "openai-compatible"

    def __init__(
        self,
        model_id: str,
        base_url: str,
        api_key_env: str = "OPENAI_API_KEY",
        timeout_seconds: float = 120.0,
    ) -> None:
        self.model_id = model_id
        self.base_url = base_url.rstrip("/")
        self.api_key_env = api_key_env
        self.timeout_seconds = timeout_seconds

    def generate(self, item: Item, config: GenerationConfig) -> Generation:
        url = self.base_url
        if not url.endswith("/chat/completions"):
            if not url.endswith("/v1"):
                url += "/v1"
            url += "/chat/completions"
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": [
                {"role": "system", "content": config.system_prompt},
                {"role": "user", "content": item.user_prompt()},
            ],
            "temperature": config.temperature,
            "max_tokens": item.max_tokens,
        }
        if config.seed is not None:
            payload["seed"] = config.seed
        headers = {"Content-Type": "application/json"}
        api_key = os.environ.get(self.api_key_env, "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:1000]
            raise RuntimeError(f"endpoint returned HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"could not reach endpoint: {exc.reason}") from exc
        latency_ms = (time.perf_counter() - started) * 1000
        choice = raw["choices"][0]
        usage = raw.get("usage", {})
        return Generation(
            text=str(choice["message"].get("content", "")),
            latency_ms=latency_ms,
            input_tokens=_optional_int(usage.get("prompt_tokens")),
            output_tokens=_optional_int(usage.get("completion_tokens")),
            finish_reason=choice.get("finish_reason"),
            raw={"id": raw.get("id"), "created": raw.get("created")},
        )


class HuggingFaceBackend(Backend):
    """Local text generation through Transformers, imported only when requested."""

    name = "huggingface"

    def __init__(self, model_id: str, revision: str | None = None, device: str = "auto") -> None:
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except ImportError as exc:
            raise RuntimeError("install local dependencies with: pip install -e '.[local]'") from exc

        self.model_id = model_id
        self.revision = revision
        self.device = device
        self._torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
        model_kwargs: dict[str, Any] = {"revision": revision, "torch_dtype": "auto"}
        if device == "auto":
            model_kwargs["device_map"] = "auto"
        self.model = AutoModelForCausalLM.from_pretrained(model_id, **model_kwargs)
        if device != "auto":
            self.model.to(device)
        self.model.eval()
        if self.tokenizer.pad_token_id is None:
            self.tokenizer.pad_token_id = self.tokenizer.eos_token_id

    def generate(self, item: Item, config: GenerationConfig) -> Generation:
        messages = [
            {"role": "system", "content": config.system_prompt},
            {"role": "user", "content": item.user_prompt()},
        ]
        if self.tokenizer.chat_template:
            rendered = self.tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        else:
            rendered = f"{config.system_prompt}\n\n{item.user_prompt()}\n\nSvar:"
        inputs = self.tokenizer(rendered, return_tensors="pt")
        target_device = next(self.model.parameters()).device
        inputs = {key: value.to(target_device) for key, value in inputs.items()}
        generation_kwargs: dict[str, Any] = {
            "max_new_tokens": item.max_tokens,
            "do_sample": config.temperature > 0,
            "pad_token_id": self.tokenizer.pad_token_id,
        }
        if config.temperature > 0:
            generation_kwargs["temperature"] = config.temperature
        if config.seed is not None:
            self._torch.manual_seed(config.seed)
        started = time.perf_counter()
        with self._torch.inference_mode():
            generated = self.model.generate(**inputs, **generation_kwargs)
        latency_ms = (time.perf_counter() - started) * 1000
        input_length = int(inputs["input_ids"].shape[-1])
        new_tokens = generated[0][input_length:]
        text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return Generation(
            text=text,
            latency_ms=latency_ms,
            input_tokens=input_length,
            output_tokens=int(new_tokens.shape[-1]),
            finish_reason="length" if int(new_tokens.shape[-1]) >= item.max_tokens else "stop",
        )


class OracleBackend(Backend):
    """Diagnostic backend that emits references. Never valid leaderboard evidence."""

    name = "oracle-diagnostic"
    model_id = "svea/oracle-diagnostic"

    def generate(self, item: Item, config: GenerationConfig) -> Generation:
        del config
        if item.id.startswith("judge::"):
            scores = {dimension: 4 for dimension in item.scoring.get("dimensions", {})}
            return Generation(
                text=json.dumps(
                    {"scores": scores, "reason": "Diagnostiskt orakelsvar."},
                    ensure_ascii=False,
                ),
                latency_ms=0.0,
                finish_reason="oracle",
            )
        scorer = item.scoring["type"]
        if scorer in {"choice", "exact"}:
            text = str(item.gold["answer"])
        elif scorer == "contains_all":
            text = str(item.gold.get("answer") or "; ".join(_first_aliases(item.gold["required"])))
        elif scorer == "numeric":
            text = str(item.gold["value"])
        elif scorer == "json_exact":
            text = json.dumps(item.gold["value"], ensure_ascii=False)
        else:
            text = str(item.gold.get("example") or item.gold.get("reference_answer") or "")
        return Generation(text=text, latency_ms=0.0, finish_reason="oracle")


def create_backend(
    kind: str,
    model_id: str,
    base_url: str | None = None,
    api_key_env: str = "OPENAI_API_KEY",
    revision: str | None = None,
    device: str = "auto",
    timeout_seconds: float = 120.0,
) -> Backend:
    if kind == "openai-compatible":
        if not base_url:
            raise ValueError("--base-url is required for the openai-compatible backend")
        return OpenAICompatibleBackend(
            model_id=model_id,
            base_url=base_url,
            api_key_env=api_key_env,
            timeout_seconds=timeout_seconds,
        )
    if kind == "huggingface":
        return HuggingFaceBackend(model_id=model_id, revision=revision, device=device)
    if kind == "oracle":
        return OracleBackend()
    raise ValueError(f"unknown backend: {kind}")


def _optional_int(value: Any) -> int | None:
    return int(value) if value is not None else None


def _first_aliases(groups: list[Any]) -> list[str]:
    return [str(group[0] if isinstance(group, list) else group) for group in groups]
