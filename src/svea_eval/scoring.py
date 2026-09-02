"""Transparent deterministic scorers and rubric-judge helpers."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from typing import Any

from .models import Item, Score


_CODE_FENCE = re.compile(r"^\s*```(?:json|text)?\s*|\s*```\s*$", re.IGNORECASE)
_CHOICE = re.compile(r"(?:^|\b)(?:svaret\s+(?:är|blir)\s+|svar\s*[:\-]?\s*)?([A-F])(?:\b|[.)])", re.IGNORECASE)
_NUMBER = re.compile(r"[-+]?\d(?:[\d\s.]*\d)?(?:[,.]\d+)?|[-+]?\d")


def normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip(" \t\r\n.,;:!?\"'`()[]{}")


def score_item(item: Item, response: str) -> Score:
    scorer = item.scoring["type"]
    try:
        if scorer == "choice":
            return _score_choice(item=item, response=response)
        if scorer == "exact":
            return _score_exact(item=item, response=response)
        if scorer == "contains_all":
            return _score_contains_all(item=item, response=response)
        if scorer == "numeric":
            return _score_numeric(item=item, response=response)
        if scorer == "json_exact":
            return _score_json(item=item, response=response)
        if scorer == "constraints":
            return _score_constraints(item=item, response=response)
        if scorer == "rubric":
            return Score(
                value=None,
                passed=None,
                scorer="rubric",
                details={"status": "judge_required"},
            )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError) as exc:
        return Score(value=0.0, passed=False, scorer=scorer, error=str(exc))
    return Score(value=0.0, passed=False, scorer=scorer, error="unsupported scorer")


def build_judge_prompt(item: Item, response: str) -> str:
    dimensions = item.scoring["dimensions"]
    rendered_dimensions = "\n".join(
        f"- {name}: {description}" for name, description in dimensions.items()
    )
    reference = item.gold.get("reference_answer", "Ingen referens; bedöm mot kriterierna.")
    required = item.gold.get("required_points", [])
    required_text = "\n".join(f"- {point}" for point in required) or "- Inga särskilda punkter."
    return (
        "Du är en strikt, opartisk bedömare av svenska modellsvar. "
        "Betygsätt varje dimension med ett heltal 0–4. Returnera endast JSON med "
        'formen {"scores":{"dimension":0},"reason":"kort motivering"}.\n\n'
        f"URSPRUNGLIG UPPGIFT\n{item.user_prompt()}\n\n"
        f"MODELLSVAR\n{response}\n\n"
        f"REFERENSSVAR\n{reference}\n\n"
        f"PUNKTER SOM BÖR FINNAS MED\n{required_text}\n\n"
        f"DIMENSIONER\n{rendered_dimensions}\n\n"
        "Skalan är 0=helt fel eller saknas, 1=stora brister, 2=delvis, "
        "3=bra med mindre brister, 4=fullt uppfyllt."
    )


def score_judgment(item: Item, judgment: str) -> Score:
    payload = _parse_json(judgment)
    scores = payload.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("judge JSON must contain a scores object")
    normalized_scores = {
        _normalize_dimension_key(str(key)): value for key, value in scores.items()
    }
    expected = list(item.scoring["dimensions"])
    parsed: dict[str, int] = {}
    for dimension in expected:
        raw = scores.get(dimension)
        if raw is None:
            raw = normalized_scores.get(_normalize_dimension_key(dimension))
        if isinstance(raw, bool) or not isinstance(raw, (int, float)):
            raise ValueError(f"judge score for {dimension!r} is not numeric")
        value = int(raw)
        if value != raw or not 0 <= value <= 4:
            raise ValueError(f"judge score for {dimension!r} must be an integer from 0 to 4")
        parsed[dimension] = value
    normalized = sum(parsed.values()) / (4 * len(parsed))
    pass_threshold = float(item.scoring.get("pass_threshold", 0.75))
    return Score(
        value=normalized,
        passed=normalized >= pass_threshold,
        scorer="rubric",
        parsed=parsed,
        details={"reason": str(payload.get("reason", "")), "raw_scale": "0-4"},
    )


def _normalize_dimension_key(value: str) -> str:
    """Match harmless judge-added Swedish diacritics without relaxing score values."""
    decomposed = unicodedata.normalize("NFKD", value).casefold()
    return "".join(
        character
        for character in decomposed
        if character.isalnum() and not unicodedata.combining(character)
    )


def _score_choice(item: Item, response: str) -> Score:
    gold = normalize_text(str(item.gold["answer"])).upper()
    match = _CHOICE.search(response.strip())
    parsed = match.group(1).upper() if match else None
    if parsed is None and item.options:
        normalized = normalize_text(response)
        for option in item.options:
            letter, _, text = option.partition(".")
            if normalize_text(text) == normalized:
                parsed = letter.strip().upper()
                break
    passed = parsed == gold
    return Score(
        value=1.0 if passed else 0.0,
        passed=passed,
        scorer="choice",
        parsed=parsed,
        details={"expected": gold, "malformed": parsed is None},
    )


def _score_exact(item: Item, response: str) -> Score:
    expected = [str(item.gold["answer"]), *[str(value) for value in item.gold.get("aliases", [])]]
    parsed = normalize_text(response)
    passed = parsed in {normalize_text(value) for value in expected}
    return Score(
        value=1.0 if passed else 0.0,
        passed=passed,
        scorer="exact",
        parsed=parsed,
        details={"accepted": expected},
    )


def _score_contains_all(item: Item, response: str) -> Score:
    normalized = normalize_text(response)
    groups: list[list[str]] = []
    for group in item.gold["required"]:
        values = group if isinstance(group, list) else [group]
        groups.append([normalize_text(str(value)) for value in values])
    matched = [any(alias in normalized for alias in group) for group in groups]
    forbidden = [normalize_text(str(value)) for value in item.gold.get("forbidden", [])]
    forbidden_hits = [value for value in forbidden if value and value in normalized]
    value = sum(matched) / len(matched) if matched else 0.0
    if forbidden_hits:
        value = 0.0
    passed = all(matched) and not forbidden_hits
    return Score(
        value=value,
        passed=passed,
        scorer="contains_all",
        parsed=response.strip(),
        details={"matched_groups": matched, "forbidden_hits": forbidden_hits},
    )


def _score_numeric(item: Item, response: str) -> Score:
    match = _NUMBER.search(response.replace("\u00a0", " "))
    if not match:
        return Score(
            value=0.0,
            passed=False,
            scorer="numeric",
            details={"malformed": True, "expected": item.gold["value"]},
        )
    raw = match.group(0).replace(" ", "")
    if "," in raw:
        raw = raw.replace(".", "").replace(",", ".")
    elif raw.count(".") > 1:
        raw = raw.replace(".", "")
    parsed = float(raw)
    expected = float(item.gold["value"])
    tolerance = float(item.scoring.get("tolerance", 0.0))
    passed = math.isclose(parsed, expected, abs_tol=tolerance, rel_tol=0.0)
    return Score(
        value=1.0 if passed else 0.0,
        passed=passed,
        scorer="numeric",
        parsed=parsed,
        details={"expected": expected, "tolerance": tolerance, "unit": item.gold.get("unit")},
    )


def _score_json(item: Item, response: str) -> Score:
    parsed = _parse_json(response)
    expected = item.gold["value"]
    accepted_values = item.gold.get("accepted_values", [])
    candidates = [expected, *accepted_values]
    subset = bool(item.scoring.get("allow_extra_keys", False))
    matched_index = next(
        (
            index
            for index, candidate in enumerate(candidates)
            if (_json_contains(parsed, candidate) if subset else parsed == candidate)
        ),
        None,
    )
    passed = matched_index is not None
    details = {"expected": expected, "allow_extra_keys": subset}
    if accepted_values:
        details["accepted_values"] = accepted_values
        details["matched_candidate"] = matched_index
    return Score(
        value=1.0 if passed else 0.0,
        passed=passed,
        scorer="json_exact",
        parsed=parsed,
        details=details,
    )


def _score_constraints(item: Item, response: str) -> Score:
    rules: dict[str, Any] = item.scoring["rules"]
    lines = [line.strip() for line in response.strip().splitlines() if line.strip()]
    checks: dict[str, bool] = {}
    if "exact_line_count" in rules:
        checks["exact_line_count"] = len(lines) == int(rules["exact_line_count"])
    if "max_words_per_line" in rules:
        maximum = int(rules["max_words_per_line"])
        checks["max_words_per_line"] = bool(lines) and all(_word_count(line) <= maximum for line in lines)
    if "total_max_words" in rules:
        checks["total_max_words"] = _word_count(response) <= int(rules["total_max_words"])
    if "required_prefixes" in rules:
        prefixes = [str(prefix) for prefix in rules["required_prefixes"]]
        checks["required_prefixes"] = len(lines) == len(prefixes) and all(
            line.startswith(prefix) for line, prefix in zip(lines, prefixes)
        )
    if "required_terms" in rules:
        normalized = normalize_text(response)
        checks["required_terms"] = all(
            normalize_text(str(term)) in normalized for term in rules["required_terms"]
        )
    if "forbidden_terms" in rules:
        normalized = normalize_text(response)
        checks["forbidden_terms"] = all(
            normalize_text(str(term)) not in normalized for term in rules["forbidden_terms"]
        )
    if "valid_json" in rules:
        try:
            _parse_json(response)
            checks["valid_json"] = True
        except (ValueError, json.JSONDecodeError):
            checks["valid_json"] = False
    value = sum(checks.values()) / len(checks) if checks else 0.0
    return Score(
        value=value,
        passed=all(checks.values()) if checks else False,
        scorer="constraints",
        parsed=response.strip(),
        details={"checks": checks},
    )


def _parse_json(response: str) -> Any:
    cleaned = _CODE_FENCE.sub("", response.strip()).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start_object, end_object = cleaned.find("{"), cleaned.rfind("}")
        start_array, end_array = cleaned.find("["), cleaned.rfind("]")
        candidates = []
        if start_object >= 0 and end_object > start_object:
            candidates.append(cleaned[start_object : end_object + 1])
        if start_array >= 0 and end_array > start_array:
            candidates.append(cleaned[start_array : end_array + 1])
        for candidate in candidates:
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError("response does not contain valid JSON")


def _json_contains(actual: Any, expected: Any) -> bool:
    if isinstance(expected, dict) and isinstance(actual, dict):
        return all(key in actual and _json_contains(actual[key], value) for key, value in expected.items())
    if isinstance(expected, list) and isinstance(actual, list):
        return actual == expected
    return actual == expected


def _word_count(value: str) -> int:
    return len(re.findall(r"\b[\wÅÄÖåäö]+\b", value, re.UNICODE))
