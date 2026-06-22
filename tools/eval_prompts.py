"""Standalone prompt-eval harness for the text-generation flow.

Runs a candidate ``SYSTEM_PROMPT`` variant against the current one over a
curated, fully synthetic corpus, prints a unified diff of the rewritten body
per input, and appends a gitignored JSONL log for later review.

The script reuses the *real* ``build_messages()`` so it exercises the exact
prompt-assembly path the app uses; the only swap is the system prompt, which is
patched in temporarily so the candidate flows through the same code. It never
writes to the database — the corpus drives **unsaved** ``Template``/``Option``
instances.

The before/after comparison is only meaningful against a **concrete** model:
``openrouter/auto:free`` can route to a different underlying model per call, so
the diff would conflate routing with the prompt change. Set
``OPENROUTER_EVAL_MODEL`` (or pass ``--model``) to a specific model.

Usage:
    uv run python tools/eval_prompts.py                 # current vs current (no-op baseline)
    uv run python tools/eval_prompts.py --candidate-file my_prompt.txt
    OPENROUTER_EVAL_MODEL=openai/gpt-4o-mini uv run python tools/eval_prompts.py
    uv run python tools/eval_prompts.py --dry-run       # build messages, no API call

Needs ``OPENROUTER_API_KEY`` (unlike ``korpo-review``).
"""

from __future__ import annotations

import argparse
import contextlib
import difflib
import json
import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import django

# Bootstrap Django before importing anything that touches models/settings.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "korpotron.settings")
django.setup()

from django.conf import settings  # noqa: E402

from core import llm  # noqa: E402
from core.models import Template  # noqa: E402

# JSONL log path (gitignored). Lives at the repo root next to manage.py.
LOG_PATH = Path(__file__).resolve().parent.parent / "eval_log.jsonl"

# Candidate prompt defaults to the current production prompt: out of the box the
# tool produces a no-op baseline (current vs current). To test a real variant,
# either edit this constant or pass ``--candidate-file PATH``.
CANDIDATE_SYSTEM_PROMPT = llm.SYSTEM_PROMPT


@dataclass(frozen=True)
class Case:
    """One synthetic eval input. ``base_prompt`` mirrors a built-in template."""

    label: str
    base_prompt: str
    generate_title: bool
    input_text: str


# Curated synthetic corpus. Every input is invented — no real user data
# (non-retention NFR). Chosen to stress faithfulness (named people, specific
# numbers, dates) and to cover each built-in template style.
CORPUS: list[Case] = [
    Case(
        label="email-fact-dense",
        base_prompt=(
            "Transform the text into a polished, well-structured business email "
            "with a clear greeting, body, and sign-off. Improve structure and "
            "readability. Preserve all information from the source."
        ),
        generate_title=True,
        input_text=(
            "tell Dana the Q3 migration slipped to Sept 14, budget is now "
            "$48,200 (up from $42k), and we lost 2 of the 5 contractors. need "
            "her sign-off by Friday."
        ),
    ),
    Case(
        label="email-terse-ambiguous",
        base_prompt=(
            "Transform the text into a polished, well-structured business email "
            "with a clear greeting, body, and sign-off. Improve structure and "
            "readability. Preserve all information from the source."
        ),
        generate_title=True,
        input_text="cant make the 3pm. move it?",
    ),
    Case(
        label="jira-fact-dense",
        base_prompt=(
            "Convert the input into a well-structured, high-quality Jira issue. "
            "Preserve all information from the source.\n\nStructure should start "
            "with a short (1-2 sentence) section with a high level description of "
            "what needs done.\n\nThe second section should describe the issue more "
            "in depth, in narrative style, explaining things like current state, "
            "reason for the change, impact, priority and dependencies.\n\nThis "
            "should be followed by two more sections with bullet point lists:\n"
            "* a TODO section (acceptance criteria)\n* an out of scope section"
        ),
        generate_title=False,
        input_text=(
            "login endpoint /api/v2/auth times out under load. p95 latency hit "
            "8.4s during the 06-18 incident, affected ~3,100 users. Marco thinks "
            "it's the unindexed sessions table. needs fix before the July 1 "
            "launch. don't touch the legacy /v1 path."
        ),
    ),
    Case(
        label="jira-terse",
        base_prompt=(
            "Convert the input into a well-structured, high-quality Jira issue. "
            "Preserve all information from the source.\n\nStructure should start "
            "with a short (1-2 sentence) section with a high level description of "
            "what needs done.\n\nThe second section should describe the issue more "
            "in depth, in narrative style, explaining things like current state, "
            "reason for the change, impact, priority and dependencies.\n\nThis "
            "should be followed by two more sections with bullet point lists:\n"
            "* a TODO section (acceptance criteria)\n* an out of scope section"
        ),
        generate_title=False,
        input_text="dark mode toggle doesnt persist after refresh",
    ),
    Case(
        label="meeting-fact-dense",
        base_prompt=(
            "Prepare structured meeting notes based on the input. Use bullet "
            "points and organize information logically. Clearly identify owners "
            "and deadlines when available. Preserve all information from the "
            "source."
        ),
        generate_title=False,
        input_text=(
            "standup 06-20: Priya finishes the export feature by Tue, Tom blocked "
            "on the staging cert (waiting on IT, ticket #4471), we agreed to cut "
            "the CSV option from v1. next sync Thursday 10am."
        ),
    ),
    Case(
        label="meeting-terse",
        base_prompt=(
            "Prepare structured meeting notes based on the input. Use bullet "
            "points and organize information logically. Clearly identify owners "
            "and deadlines when available. Preserve all information from the "
            "source."
        ),
        generate_title=False,
        input_text="quick sync, decided to ship friday, Sam owns the release",
    ),
]


@contextlib.contextmanager
def _patched_system_prompt(prompt: str) -> Iterator[None]:
    """Temporarily swap ``llm.SYSTEM_PROMPT`` so the real ``build_messages``
    assembles the candidate prompt through the exact production path."""
    original = llm.SYSTEM_PROMPT
    llm.SYSTEM_PROMPT = prompt
    try:
        yield
    finally:
        llm.SYSTEM_PROMPT = original


def _build_for(case: Case, system_prompt: str) -> list:
    """Build the messages list for a case under a given system prompt.

    Drives the real ``build_messages`` with an unsaved ``Template`` (no DB
    write). No options are applied — the corpus exercises base templates.
    """
    template = Template(
        name=case.label,
        base_prompt=case.base_prompt,
        generate_title=case.generate_title,
    )
    with _patched_system_prompt(system_prompt):
        return llm.build_messages(template, [], case.input_text)


def _call(model: str, messages: list) -> str:
    """Run one eval completion at ``temperature=0`` and return the raw body.

    temperature=0 pins sampling so the diff is attributable to the prompt
    change, not noise. Reuses the app's configured OpenRouter client.
    """
    client = llm._get_client()
    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    raw = completion.choices[0].message.content or ""
    return llm.parse_result(raw).body


def _resolve_model(cli_model: str | None) -> str:
    """--model flag > OPENROUTER_EVAL_MODEL env > settings.OPENROUTER_MODEL."""
    return (
        cli_model
        or os.environ.get("OPENROUTER_EVAL_MODEL")
        or settings.OPENROUTER_MODEL
    )


def _print_diff(label: str, current: str, candidate: str) -> None:
    diff = difflib.unified_diff(
        current.splitlines(),
        candidate.splitlines(),
        fromfile=f"{label} [current]",
        tofile=f"{label} [candidate]",
        lineterm="",
    )
    printed = False
    for line in diff:
        print(line)
        printed = True
    if not printed:
        print(f"(no difference for {label})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model",
        default=None,
        help="Eval model id (overrides OPENROUTER_EVAL_MODEL and settings).",
    )
    parser.add_argument(
        "--candidate-file",
        type=Path,
        default=None,
        help="Path to a text file holding the candidate SYSTEM_PROMPT.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the messages for each case; make no API call.",
    )
    args = parser.parse_args(argv)

    candidate_prompt = CANDIDATE_SYSTEM_PROMPT
    if args.candidate_file is not None:
        candidate_prompt = args.candidate_file.read_text(encoding="utf-8")

    if args.dry_run:
        for case in CORPUS:
            print(f"=== {case.label} (candidate messages) ===")
            for msg in _build_for(case, candidate_prompt):
                print(f"--- {msg['role']} ---")
                print(msg["content"])
            print()
        return 0

    if not settings.OPENROUTER_API_KEY:
        print(
            "Error: OPENROUTER_API_KEY is not set. Set it in .env (this tool "
            "makes real API calls, unlike korpo-review).",
            file=sys.stderr,
        )
        return 2

    model = _resolve_model(args.model)
    if "auto" in model:
        print(
            f"Warning: eval model is '{model}'. Auto-routing can pick a "
            "different underlying model per call, making the before/after diff "
            "unreliable. Set OPENROUTER_EVAL_MODEL to a concrete model.",
            file=sys.stderr,
        )

    print(f"Eval model: {model}  (temperature=0)\n")

    with LOG_PATH.open("a", encoding="utf-8") as log:
        for case in CORPUS:
            current_msgs = _build_for(case, llm.SYSTEM_PROMPT)
            candidate_msgs = _build_for(case, candidate_prompt)

            current_body = _call(model, current_msgs)
            candidate_body = _call(model, candidate_msgs)

            print(f"=== {case.label} ===")
            _print_diff(case.label, current_body, candidate_body)
            print()

            log.write(
                json.dumps(
                    {
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "model": model,
                        "label": case.label,
                        "input_text": case.input_text,
                        "current_body": current_body,
                        "candidate_body": candidate_body,
                    }
                )
                + "\n"
            )

    print(f"Wrote log: {LOG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
