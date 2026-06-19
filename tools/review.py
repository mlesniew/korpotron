"""Agentic code review CLI tool using the Claude Agent SDK.

Reads a git diff from stdin, runs a structured two-turn review, and prints
a JSON review to stdout with cost/usage on stderr. Exit code reflects verdict:
0 = pass, 1 = fail, 2 = error.

Usage: git diff | uv run python tools/review.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Literal

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage
from claude_agent_sdk import query as _sdk_query
from pydantic import BaseModel, ConfigDict, Field

# Patchable reference for future tests
query = _sdk_query

MAX_BUDGET_USD = 0.5

SYSTEM_PROMPT = (
    "You are a precise, constructive code reviewer evaluating a pull request diff. "
    "Score the diff on five criteria, each on a scale of 1 to 10 (1 = very poor, 10 = excellent):\n"
    "  1. implementation_correctness — does the code do what it claims?\n"
    "  2. idiomaticity — does it follow language and project conventions?\n"
    "  3. complexity — is it as simple as the problem allows?\n"
    "  4. test_risk_coverage — are tests proportional to the risk introduced?\n"
    "  5. security_safety — are there no vulnerabilities, secret leaks, or unsafe patterns?\n\n"
    "Then issue a binding verdict: 'pass' if the change is acceptable as-is, 'fail' if it needs "
    "rework before merging. Provide a concise Markdown summary suitable for a PR comment."
)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid")

    implementation_correctness: int = Field(
        description="Does the code do what it declares (scale 1-10, no defaults)."
    )
    idiomaticity: int = Field(
        description="Conformance with language and project conventions (scale 1-10)."
    )
    complexity: int = Field(
        description="Simplicity relative to the problem — higher is simpler (scale 1-10)."
    )
    test_risk_coverage: int = Field(
        description="Test coverage proportional to risk introduced (scale 1-10)."
    )
    security_safety: int = Field(
        description="No vulnerabilities, secret leaks, or unsafe patterns (scale 1-10)."
    )
    verdict: Literal["pass", "fail"] = Field(
        description="Binding verdict for the whole change."
    )
    summary: str = Field(description="Markdown summary, ready as a PR comment.")


async def run_review(diff: str) -> tuple[Review, ResultMessage]:
    """Run the review agent and return (Review, ResultMessage) on success."""
    if not diff.strip():
        raise ValueError("Empty diff — nothing to review.")

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        model="claude-sonnet-4-6",
        max_turns=2,
        allowed_tools=[],
        setting_sources=[],
        output_format={"type": "json_schema", "schema": Review.model_json_schema()},
        max_budget_usd=MAX_BUDGET_USD,
    )

    result_message: ResultMessage | None = None
    async for message in query(prompt=f"Review this diff:\n\n{diff}", options=options):
        if isinstance(message, ResultMessage):
            result_message = message

    if result_message is None:
        raise RuntimeError("The agent returned no result message.")
    if result_message.subtype != "success":
        errors = "; ".join(result_message.errors or [])
        raise RuntimeError(f"Review failed ({result_message.subtype}): {errors}")

    review = Review.model_validate(result_message.structured_output)
    return review, result_message


def main() -> int:
    diff = sys.stdin.read()
    try:
        review, result = asyncio.run(run_review(diff))
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(review.model_dump(), indent=2))

    cost = (
        f"${result.total_cost_usd:.4f}" if result.total_cost_usd is not None else "n/a"
    )
    usage = result.usage or {}
    print(
        f"Cost: {cost} | "
        f"Tokens in: {usage.get('input_tokens', 'n/a')} "
        f"out: {usage.get('output_tokens', 'n/a')} | "
        f"Turns: {result.num_turns}",
        file=sys.stderr,
    )

    return 0 if review.verdict == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
