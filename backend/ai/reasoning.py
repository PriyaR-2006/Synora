import json
import os

from openai import OpenAI


DEFAULT_MODEL = "gpt-5.6-luna"


SYSTEM_PROMPT = """
You are the reasoning layer of Synora, an AI storage-management agent.

Your job is to understand the user's storage-management request and convert
it into a safe structured mission.

You DO NOT directly modify, delete, move, or compress files.

The deterministic Synora planner and executor are responsible for actual
file operations and safety checks.

Return ONLY valid JSON with this structure:

{
    "goal": "short description of the goal",
    "target_storage_bytes": integer,
    "constraints": [
        "constraint 1",
        "constraint 2"
    ],
    "strategy": "short description of the preferred strategy"
}

Rules:

1. Never invent a storage target when the user gives one.
2. Convert KB, MB, GB and TB into bytes.
3. If the user does not specify an exact target, use 0.
4. Preserve safety-related constraints.
5. Never instruct Synora to delete protected or high-risk files.
6. Prefer reversible actions such as compression and quarantine.
7. Do not include markdown.
"""


def _get_client() -> OpenAI:
    """
    Create an OpenAI client using the OPENAI_API_KEY
    environment variable.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set."
        )

    return OpenAI(api_key=api_key)


def understand_goal(
    user_request: str,
    model: str = DEFAULT_MODEL,
) -> dict:
    """
    Convert a natural-language storage request into
    a structured Synora mission.
    """

    if not user_request.strip():
        raise ValueError(
            "User request cannot be empty."
        )

    client = _get_client()

    response = client.responses.create(
        model=model,
        instructions=SYSTEM_PROMPT,
        input=user_request,
    )

    text = response.output_text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "AI returned invalid JSON."
        ) from error

    required_fields = {
        "goal",
        "target_storage_bytes",
        "constraints",
        "strategy",
    }

    missing = required_fields - result.keys()

    if missing:
        raise RuntimeError(
            f"AI response is missing fields: {missing}"
        )

    if not isinstance(
        result["target_storage_bytes"],
        int,
    ):
        raise RuntimeError(
            "target_storage_bytes must be an integer."
        )

    if result["target_storage_bytes"] < 0:
        raise RuntimeError(
            "target_storage_bytes cannot be negative."
        )

    if not isinstance(
        result["constraints"],
        list,
    ):
        raise RuntimeError(
            "constraints must be a list."
        )

    return result