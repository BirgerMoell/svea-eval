"""Suite loading and validation."""

from __future__ import annotations

import json
from importlib.resources import files
from pathlib import Path
from typing import Any, Iterable

from .models import Item


SUPPORTED_SCORERS = {"choice", "exact", "contains_all", "numeric", "json_exact", "constraints", "rubric"}
SUPPORTED_SPLITS = {"dev", "validation", "test_public", "test_private"}
SUPPORTED_VARIANTS = {"base", "challenge", "clean", "distractor", "supported", "insufficient", "free", "strict"}


def bundled_suite_dir() -> Path:
    return Path(str(files("svea_eval").joinpath("resources/suites/svea-core-v0.1")))


def resolve_suite(path: str | Path | None = None) -> Path:
    if path is None:
        return bundled_suite_dir()
    candidate = Path(path).expanduser().resolve()
    if candidate.is_file():
        candidate = candidate.parent
    return candidate


def load_suite(path: str | Path | None = None) -> tuple[dict[str, Any], list[Item]]:
    suite_dir = resolve_suite(path)
    metadata = json.loads((suite_dir / "suite.json").read_text(encoding="utf-8"))
    items: list[Item] = []
    data_path = suite_dir / metadata.get("data_file", "dev.jsonl")
    for line_number, line in enumerate(data_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            items.append(Item.from_dict(json.loads(line)))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"{data_path}:{line_number}: invalid item: {exc}") from exc
    return metadata, items


def validate_suite(metadata: dict[str, Any], items: Iterable[Item]) -> list[str]:
    errors: list[str] = []
    required_meta = {"id", "version", "name", "status", "data_file", "domains", "task_types"}
    missing_meta = sorted(required_meta - metadata.keys())
    if missing_meta:
        errors.append(f"suite.json is missing: {', '.join(missing_meta)}")

    seen: set[str] = set()
    pair_members: dict[str, list[Item]] = {}
    materialized = list(items)
    if not materialized:
        errors.append("suite contains no items")
        return errors

    for item in materialized:
        prefix = item.id
        if item.id in seen:
            errors.append(f"{prefix}: duplicate id")
        seen.add(item.id)
        if item.suite_id != metadata.get("id"):
            errors.append(f"{prefix}: suite_id does not match suite.json")
        if item.suite_version != metadata.get("version"):
            errors.append(f"{prefix}: suite_version does not match suite.json")
        if item.split not in SUPPORTED_SPLITS:
            errors.append(f"{prefix}: unsupported split {item.split!r}")
        if item.scoring.get("type") not in SUPPORTED_SCORERS:
            errors.append(f"{prefix}: unsupported scorer {item.scoring.get('type')!r}")
        if not item.source.url or not item.source.license:
            errors.append(f"{prefix}: source URL and license are required")
        if not item.prompt.strip():
            errors.append(f"{prefix}: prompt is empty")
        if item.max_tokens < 1:
            errors.append(f"{prefix}: max_tokens must be positive")
        if item.variant and item.variant not in SUPPORTED_VARIANTS:
            errors.append(f"{prefix}: unsupported variant {item.variant!r}")
        if item.pair_id:
            pair_members.setdefault(item.pair_id, []).append(item)
        elif item.variant:
            errors.append(f"{prefix}: variant requires pair_id")
        _validate_gold(item=item, errors=errors)

    for pair_id, members in pair_members.items():
        if len(members) != 2:
            errors.append(f"pair {pair_id!r}: expected exactly 2 members, found {len(members)}")
        variants = [member.variant for member in members]
        if len(set(variants)) != len(variants):
            errors.append(f"pair {pair_id!r}: variants must be unique")

    declared_domains = set(metadata.get("domains", []))
    actual_domains = {item.domain for item in materialized}
    if actual_domains != declared_domains:
        errors.append(
            "suite domains differ from data: "
            f"declared={sorted(declared_domains)}, actual={sorted(actual_domains)}"
        )
    declared_tasks = set(metadata.get("task_types", []))
    actual_tasks = {item.task_type for item in materialized}
    if actual_tasks != declared_tasks:
        errors.append(
            "suite task types differ from data: "
            f"declared={sorted(declared_tasks)}, actual={sorted(actual_tasks)}"
        )
    return errors


def _validate_gold(item: Item, errors: list[str]) -> None:
    scorer = item.scoring.get("type")
    if scorer in {"choice", "exact"} and "answer" not in item.gold:
        errors.append(f"{item.id}: {scorer} scorer requires gold.answer")
    elif scorer == "contains_all" and not item.gold.get("required"):
        errors.append(f"{item.id}: contains_all scorer requires gold.required")
    elif scorer == "numeric" and "value" not in item.gold:
        errors.append(f"{item.id}: numeric scorer requires gold.value")
    elif scorer == "json_exact" and "value" not in item.gold:
        errors.append(f"{item.id}: json_exact scorer requires gold.value")
    elif scorer == "constraints" and not item.scoring.get("rules"):
        errors.append(f"{item.id}: constraints scorer requires scoring.rules")
    elif scorer == "rubric" and not item.scoring.get("dimensions"):
        errors.append(f"{item.id}: rubric scorer requires scoring.dimensions")
