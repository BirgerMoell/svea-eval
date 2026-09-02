"""Command-line interface for SVEA Eval."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .backends import DEFAULT_SYSTEM_PROMPT, GenerationConfig, create_backend
from .data import load_suite, resolve_suite, validate_suite
from .reporting import render_text_report
from .runner import run_evaluation
from .site import build_site_data


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="svea",
        description="Swedish-first capability evaluation for local and API language models.",
    )
    parser.add_argument("--version", action="version", version=f"svea-eval {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List suite coverage")
    list_parser.add_argument("--suite", type=Path)
    list_parser.add_argument("--json", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="Validate suite data and metadata")
    validate_parser.add_argument("--suite", type=Path)

    run_parser = subparsers.add_parser("run", help="Run or resume an evaluation")
    run_parser.add_argument("--suite", type=Path)
    run_parser.add_argument(
        "--backend",
        choices=["openai-compatible", "ollama", "huggingface", "oracle"],
        required=True,
    )
    run_parser.add_argument("--model", required=True)
    run_parser.add_argument("--revision")
    run_parser.add_argument("--base-url")
    run_parser.add_argument("--api-key-env", default="OPENAI_API_KEY")
    run_parser.add_argument("--device", default="auto")
    run_parser.add_argument("--timeout", type=float, default=120.0)
    run_parser.add_argument(
        "--ollama-think",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="allow Ollama thinking tokens (disabled by default for answer-budget fidelity)",
    )
    run_parser.add_argument("--temperature", type=float, default=0.0)
    run_parser.add_argument("--seed", type=_optional_int, default=17, metavar="INT|none")
    run_parser.add_argument("--system-prompt", default=DEFAULT_SYSTEM_PROMPT)
    run_parser.add_argument("--limit", type=int)
    run_parser.add_argument("--domain", action="append", default=[])
    run_parser.add_argument("--task-type", action="append", default=[])
    run_parser.add_argument("--output", type=Path, required=True)
    run_parser.add_argument("--run-id")
    run_parser.add_argument("--diagnostic", action="store_true")
    run_parser.add_argument(
        "--judge-backend",
        choices=["openai-compatible", "ollama", "huggingface", "oracle"],
    )
    run_parser.add_argument("--judge-model")
    run_parser.add_argument("--judge-base-url")
    run_parser.add_argument("--judge-api-key-env", default="OPENAI_API_KEY")
    run_parser.add_argument("--judge-revision")

    report_parser = subparsers.add_parser("report", help="Print a saved run summary")
    report_parser.add_argument("run", type=Path)
    report_parser.add_argument("--json", action="store_true")

    site_parser = subparsers.add_parser("build-site", help="Refresh GitHub Pages data")
    site_parser.add_argument("--docs", type=Path, default=Path("docs"))
    site_parser.add_argument("--results", type=Path, default=Path("results/runs"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "list":
            return _list_suite(args)
        if args.command == "validate":
            return _validate(args)
        if args.command == "run":
            return _run(args)
        if args.command == "report":
            return _report(args)
        if args.command == "build-site":
            return _build_site(args)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _list_suite(args: argparse.Namespace) -> int:
    metadata, items = load_suite(args.suite)
    payload: dict[str, Any] = {
        "id": metadata["id"],
        "version": metadata["version"],
        "status": metadata["status"],
        "path": str(resolve_suite(args.suite)),
        "items": len(items),
        "domains": {
            domain: len([item for item in items if item.domain == domain])
            for domain in metadata["domains"]
        },
        "task_types": {
            task: len([item for item in items if item.task_type == task])
            for task in metadata["task_types"]
        },
        "contrast_pairs": len({item.pair_id for item in items if item.pair_id}),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{payload['id']} v{payload['version']} — {payload['status']}")
        print(f"{payload['items']} items · {payload['contrast_pairs']} contrast pairs")
        print("Domains:")
        for name, count in payload["domains"].items():
            print(f"  {name:<24} {count}")
        print("Task types:")
        for name, count in payload["task_types"].items():
            print(f"  {name:<24} {count}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    metadata, items = load_suite(args.suite)
    errors = validate_suite(metadata=metadata, items=items)
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print(
        f"OK {metadata['id']} v{metadata['version']}: {len(items)} items, "
        f"{len(metadata['domains'])} domains, {len(metadata['task_types'])} task types"
    )
    return 0


def _run(args: argparse.Namespace) -> int:
    metadata, items = load_suite(args.suite)
    errors = validate_suite(metadata=metadata, items=items)
    if errors:
        raise ValueError("suite validation failed:\n" + "\n".join(errors))
    backend = create_backend(
        kind=args.backend,
        model_id=args.model,
        base_url=args.base_url,
        api_key_env=args.api_key_env,
        revision=args.revision,
        device=args.device,
        timeout_seconds=args.timeout,
        ollama_think=args.ollama_think,
    )
    judge_backend = None
    if args.judge_backend:
        if not args.judge_model and args.judge_backend != "oracle":
            raise ValueError("--judge-model is required when --judge-backend is set")
        judge_backend = create_backend(
            kind=args.judge_backend,
            model_id=args.judge_model or "svea/oracle-diagnostic",
            base_url=args.judge_base_url or args.base_url,
            api_key_env=args.judge_api_key_env,
            revision=args.judge_revision,
            device=args.device,
            timeout_seconds=args.timeout,
            ollama_think=args.ollama_think,
        )
    config = GenerationConfig(
        temperature=args.temperature,
        seed=args.seed,
        system_prompt=args.system_prompt,
    )
    run = run_evaluation(
        suite_metadata=metadata,
        items=items,
        backend=backend,
        output=args.output,
        config=config,
        model_revision=args.revision,
        judge_backend=judge_backend,
        judge_revision=args.judge_revision,
        limit=args.limit,
        domains=set(args.domain),
        task_types=set(args.task_type),
        run_id=args.run_id,
        diagnostic=args.diagnostic,
    )
    print(render_text_report(run))
    print(f"\nSaved {args.output.resolve()}")
    return 0 if run["status"] in {"completed", "partial"} else 1


def _report(args: argparse.Namespace) -> int:
    run = json.loads(args.run.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(run["summary"], ensure_ascii=False, indent=2))
    else:
        print(render_text_report(run))
    return 0


def _build_site(args: argparse.Namespace) -> int:
    result = build_site_data(docs_dir=args.docs.resolve(), results_dir=args.results.resolve())
    print(
        f"Built {args.docs.resolve() / 'data'} for {result['catalog']['suite']['items']} items "
        f"and {result['runs']} publishable runs"
    )
    return 0


def _optional_int(value: str) -> int | None:
    if value.casefold() in {"none", "null", "off"}:
        return None
    return int(value)
