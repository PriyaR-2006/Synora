import json
import os
import re
from typing import Any, Optional


DEFAULT_ANTHROPIC_MODEL = "claude-sonnet-4-5"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


SYSTEM_PROMPT = """
You are the Goal Interpreter of Synora, an autonomous digital steward for
goal-driven file management.

Your job is to understand the user's storage-management request and convert
it into a safe structured mission description.

You DO NOT directly modify, delete, move, or compress files. The
deterministic Synora planner and executor are responsible for actual file
operations and safety checks.

Return ONLY valid JSON with this exact structure and nothing else:

{
    "goal": "short description of the goal",
    "target_storage_bytes": integer,
    "constraints": {
        "delete_prohibited": true or false,
        "protect_sensitive_data": true or false,
        "workspace": "a directory path mentioned by the user, or null",
        "approval_required_for": ["list", "of", "action", "types"]
    },
    "strategy": "short description of the preferred strategy"
}

Rules:

1. Never invent a storage target when the user gives one.
2. Convert KB, MB, GB and TB into bytes (1 KB = 1024 bytes).
3. If the user does not specify an exact target, use 0.
4. delete_prohibited defaults to true unless the user clearly asks for
   deletion to be allowed.
5. protect_sensitive_data defaults to true.
6. Never instruct Synora to delete protected or high-risk files.
7. Prefer reversible actions such as compression and quarantine.
8. Do not include markdown, comments, or any text outside the JSON object.
"""


REQUIRED_TOP_LEVEL_FIELDS = {
    "goal",
    "target_storage_bytes",
    "constraints",
    "strategy",
}

REQUIRED_CONSTRAINT_FIELDS = {
    "delete_prohibited",
    "protect_sensitive_data",
    "workspace",
    "approval_required_for",
}


class GoalInterpretationError(RuntimeError):
    """Raised when neither an LLM call nor the fallback interpreter can
    produce a usable structured goal (in practice this should be rare,
    since the fallback interpreter always succeeds on non-empty input)."""


# ---------------------------------------------------------------------------
# Unit conversion helpers (shared by both the LLM-normalization path and
# the deterministic fallback).
# ---------------------------------------------------------------------------

_UNIT_MULTIPLIERS = {
    "b": 1,
    "byte": 1,
    "bytes": 1,
    "kb": 1024,
    "mb": 1024 ** 2,
    "gb": 1024 ** 3,
    "tb": 1024 ** 4,
}

_SIZE_PATTERN = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>tb|gb|mb|kb|bytes?|b)\b",
    re.IGNORECASE,
)


def _extract_target_bytes(text: str) -> int:
    match = _SIZE_PATTERN.search(text)

    if not match:
        return 0

    value = float(match.group("value"))
    unit = match.group("unit").lower()

    multiplier = _UNIT_MULTIPLIERS.get(unit, 1)

    return int(value * multiplier)


def _fallback_interpret(user_request: str) -> dict[str, Any]:
    """
    Deterministic, dependency-free interpreter used whenever no LLM
    provider is configured or the LLM call fails. Keyword/regex based,
    intentionally conservative (defaults to the safest constraints).
    """

    lowered = user_request.lower()

    target_bytes = _extract_target_bytes(user_request)

    delete_prohibited = True
    if re.search(r"\ballow(ed)?\s+to\s+delete\b", lowered) or re.search(
        r"\bdeletion\s+is\s+allowed\b", lowered
    ):
        delete_prohibited = False

    protect_sensitive_data = True

    approval_required_for: list[str] = []
    if "overwrite" in lowered:
        approval_required_for.append("OVERWRITE")
    if "delete" in lowered:
        approval_required_for.append("DELETE")
    if "export" in lowered or "upload" in lowered:
        approval_required_for.append("SENSITIVE_EXPORT")

    workspace_match = re.search(
        r"(?:in|under|inside)\s+([./~][^\s,]+|[A-Za-z]:\\\S+)",
        user_request,
    )
    workspace = workspace_match.group(1) if workspace_match else None

    strategy = "Prefer reversible actions (compression, quarantine); avoid deletion."

    return {
        "goal": user_request.strip()[:200] or "Recover storage safely",
        "target_storage_bytes": target_bytes,
        "constraints": {
            "delete_prohibited": delete_prohibited,
            "protect_sensitive_data": protect_sensitive_data,
            "workspace": workspace,
            "approval_required_for": approval_required_for,
        },
        "strategy": strategy,
    }


# ---------------------------------------------------------------------------
# LLM call paths
# ---------------------------------------------------------------------------

def _call_anthropic(user_request: str, model: str) -> str:
    import anthropic

    client = anthropic.Anthropic()

    response = client.messages.create(
        model=model,
        max_tokens=1000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_request}],
    )

    text_parts = [
        block.text
        for block in response.content
        if getattr(block, "type", None) == "text"
    ]

    return "".join(text_parts).strip()


def _call_openai(user_request: str, model: str) -> str:
    from openai import OpenAI

    client = OpenAI()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_request},
        ],
    )

    return response.choices[0].message.content.strip()


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()

    if stripped.startswith("```"):
        stripped = re.sub(r"^```[a-zA-Z]*\n?", "", stripped)
        stripped = re.sub(r"\n?```$", "", stripped)

    return stripped.strip()


def _normalize_llm_result(raw: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED_TOP_LEVEL_FIELDS - raw.keys()

    if missing:
        raise GoalInterpretationError(
            f"LLM response is missing fields: {missing}"
        )

    if not isinstance(raw["target_storage_bytes"], int):
        raise GoalInterpretationError(
            "target_storage_bytes must be an integer."
        )

    if raw["target_storage_bytes"] < 0:
        raise GoalInterpretationError(
            "target_storage_bytes cannot be negative."
        )

    constraints = raw.get("constraints")

    if not isinstance(constraints, dict):
        raise GoalInterpretationError("constraints must be an object.")

    missing_constraints = REQUIRED_CONSTRAINT_FIELDS - constraints.keys()

    if missing_constraints:
        raise GoalInterpretationError(
            f"constraints is missing fields: {missing_constraints}"
        )

    if not isinstance(constraints["approval_required_for"], list):
        raise GoalInterpretationError(
            "constraints.approval_required_for must be a list."
        )

    return {
        "goal": str(raw["goal"]),
        "target_storage_bytes": int(raw["target_storage_bytes"]),
        "constraints": {
            "delete_prohibited": bool(constraints["delete_prohibited"]),
            "protect_sensitive_data": bool(
                constraints["protect_sensitive_data"]
            ),
            "workspace": constraints.get("workspace"),
            "approval_required_for": list(
                constraints["approval_required_for"]
            ),
        },
        "strategy": str(raw.get("strategy", "")),
    }


def understand_goal(
    user_request: str,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """
    Convert a natural-language storage request into a structured Synora
    mission description.

    Provider selection:
        - ANTHROPIC_API_KEY set -> uses Anthropic (Claude).
        - else OPENAI_API_KEY set -> uses OpenAI.
        - else, or on any error from either provider -> falls back to
          the deterministic keyword-based interpreter.

    This function never raises for a merely-unavailable LLM; it only
    raises GoalInterpretationError for a genuinely empty request, or if
    a returned LLM response fails schema validation and the fallback
    itself is somehow inapplicable (which in practice never happens,
    since the fallback only requires a non-empty string).
    """

    if not user_request or not user_request.strip():
        raise GoalInterpretationError("User request cannot be empty.")

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if anthropic_key:
        try:
            raw_text = _call_anthropic(
                user_request,
                model or DEFAULT_ANTHROPIC_MODEL,
            )
            return _normalize_llm_result(
                json.loads(_strip_code_fences(raw_text))
            )
        except Exception:
            # Any failure (missing package, network error, bad JSON,
            # schema mismatch) falls through to OpenAI, then to the
            # deterministic fallback below.
            pass

    if openai_key:
        try:
            raw_text = _call_openai(
                user_request,
                model or DEFAULT_OPENAI_MODEL,
            )
            return _normalize_llm_result(
                json.loads(_strip_code_fences(raw_text))
            )
        except Exception:
            pass

    return _fallback_interpret(user_request)