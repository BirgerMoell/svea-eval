"""Typed data contracts used throughout SVEA Eval."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Source:
    kind: str
    title: str
    url: str
    license: str
    accessed: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Source":
        return cls(
            kind=str(value["kind"]),
            title=str(value["title"]),
            url=str(value["url"]),
            license=str(value["license"]),
            accessed=str(value["accessed"]) if value.get("accessed") else None,
        )


@dataclass(frozen=True)
class Item:
    id: str
    suite_id: str
    suite_version: str
    split: str
    domain: str
    capability: str
    task_type: str
    prompt: str
    gold: dict[str, Any]
    scoring: dict[str, Any]
    source: Source
    context: str = ""
    options: tuple[str, ...] = ()
    pair_id: str | None = None
    variant: str | None = None
    tags: tuple[str, ...] = ()
    max_tokens: int = 128
    review_status: str = "author_reviewed"
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Item":
        return cls(
            id=str(value["id"]),
            suite_id=str(value["suite_id"]),
            suite_version=str(value["suite_version"]),
            split=str(value["split"]),
            domain=str(value["domain"]),
            capability=str(value["capability"]),
            task_type=str(value["task_type"]),
            prompt=str(value["prompt"]),
            context=str(value.get("context", "")),
            options=tuple(str(option) for option in value.get("options", [])),
            gold=dict(value["gold"]),
            scoring=dict(value["scoring"]),
            source=Source.from_dict(value["source"]),
            pair_id=str(value["pair_id"]) if value.get("pair_id") else None,
            variant=str(value["variant"]) if value.get("variant") else None,
            tags=tuple(str(tag) for tag in value.get("tags", [])),
            max_tokens=int(value.get("max_tokens", 128)),
            review_status=str(value.get("review_status", "author_reviewed")),
            metadata=dict(value.get("metadata", {})),
        )

    def user_prompt(self) -> str:
        sections: list[str] = []
        if self.context:
            sections.extend(["UNDERLAG", self.context.strip(), ""])
        sections.extend(["UPPGIFT", self.prompt.strip()])
        if self.options:
            sections.append("")
            sections.append("SVARSALTERNATIV")
            sections.extend(self.options)
        return "\n".join(sections).strip()


@dataclass(frozen=True)
class Generation:
    text: str
    latency_ms: float
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(frozen=True)
class Score:
    value: float | None
    passed: bool | None
    scorer: str
    parsed: Any = None
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
