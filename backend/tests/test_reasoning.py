"""
Tests for ai/reasoning.py - Goal Interpreter provider selection and
fallback behaviour.

No real network calls are made: provider functions (_call_groq,
_call_anthropic, _call_openai) are monkeypatched directly so these
tests run offline and never require a real API key.
"""

import pytest

from ai import reasoning
from ai.reasoning import (
    GoalInterpretationError,
    _normalize_llm_result,
    understand_goal,
)


VALID_LLM_JSON = """
{
    "goal": "Free up storage safely",
    "target_storage_bytes": 1048576,
    "constraints": {
        "delete_prohibited": true,
        "protect_sensitive_data": true,
        "workspace": "./project",
        "approval_required_for": ["OVERWRITE"]
    },
    "strategy": "Compress large files first."
}
"""


def _clear_all_provider_keys(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


# ---------------------------------------------------------------------------
# Deterministic fallback (no keys configured)
# ---------------------------------------------------------------------------

def test_fallback_used_when_no_keys_configured(monkeypatch):
    _clear_all_provider_keys(monkeypatch)

    result = understand_goal("Free up 500 MB in ./data without deleting anything")

    assert result["target_storage_bytes"] == 500 * 1024 * 1024
    assert result["constraints"]["delete_prohibited"] is True
    assert result["constraints"]["workspace"] == "./data"


def test_fallback_raises_on_empty_request(monkeypatch):
    _clear_all_provider_keys(monkeypatch)

    with pytest.raises(GoalInterpretationError):
        understand_goal("")


def test_fallback_allows_deletion_when_stated(monkeypatch):
    _clear_all_provider_keys(monkeypatch)

    result = understand_goal("deletion is allowed, recover 2 GB")

    assert result["constraints"]["delete_prohibited"] is False
    assert result["target_storage_bytes"] == 2 * 1024 ** 3


# ---------------------------------------------------------------------------
# Groq is tried first when GROQ_API_KEY is set
# ---------------------------------------------------------------------------

def test_groq_used_when_key_present_and_call_succeeds(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    monkeypatch.setattr(
        reasoning, "_call_groq", lambda user_request, model: VALID_LLM_JSON
    )

    result = understand_goal("some request")

    assert result["goal"] == "Free up storage safely"
    assert result["target_storage_bytes"] == 1048576
    assert result["strategy"] == "Compress large files first."


def test_groq_failure_falls_through_to_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _raise(user_request, model):
        raise RuntimeError("simulated network/auth failure")

    monkeypatch.setattr(reasoning, "_call_groq", _raise)

    result = understand_goal("Free up 1 GB in ./x")

    # Fell through to the deterministic fallback rather than raising.
    assert result["target_storage_bytes"] == 1024 ** 3


def test_groq_invalid_json_falls_through_to_fallback(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    monkeypatch.setattr(
        reasoning, "_call_groq", lambda user_request, model: "not valid json"
    )

    result = understand_goal("Free up 1 GB")

    assert result["target_storage_bytes"] == 1024 ** 3


def test_groq_missing_schema_fields_falls_through(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key-for-test")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    monkeypatch.setattr(
        reasoning,
        "_call_groq",
        lambda user_request, model: '{"goal": "x", "target_storage_bytes": 5}',
    )

    result = understand_goal("Free up 1 GB")

    assert result["target_storage_bytes"] == 1024 ** 3


# ---------------------------------------------------------------------------
# Provider priority: Groq > Anthropic > OpenAI > fallback
# ---------------------------------------------------------------------------

def test_groq_takes_priority_over_anthropic_and_openai(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

    calls = {"groq": 0, "anthropic": 0, "openai": 0}

    def _groq(user_request, model):
        calls["groq"] += 1
        return VALID_LLM_JSON

    def _anthropic(user_request, model):
        calls["anthropic"] += 1
        return VALID_LLM_JSON

    def _openai(user_request, model):
        calls["openai"] += 1
        return VALID_LLM_JSON

    monkeypatch.setattr(reasoning, "_call_groq", _groq)
    monkeypatch.setattr(reasoning, "_call_anthropic", _anthropic)
    monkeypatch.setattr(reasoning, "_call_openai", _openai)

    understand_goal("some request")

    assert calls["groq"] == 1
    assert calls["anthropic"] == 0
    assert calls["openai"] == 0


def test_falls_through_groq_to_anthropic_when_groq_fails(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    def _groq_fails(user_request, model):
        raise RuntimeError("groq down")

    def _anthropic_succeeds(user_request, model):
        return VALID_LLM_JSON

    monkeypatch.setattr(reasoning, "_call_groq", _groq_fails)
    monkeypatch.setattr(reasoning, "_call_anthropic", _anthropic_succeeds)

    result = understand_goal("some request")

    assert result["goal"] == "Free up storage safely"


def test_falls_through_all_providers_to_fallback_when_all_fail(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-groq-key")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-anthropic-key")
    monkeypatch.setenv("OPENAI_API_KEY", "fake-openai-key")

    def _fail(user_request, model):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(reasoning, "_call_groq", _fail)
    monkeypatch.setattr(reasoning, "_call_anthropic", _fail)
    monkeypatch.setattr(reasoning, "_call_openai", _fail)

    result = understand_goal("Free up 3 MB")

    assert result["target_storage_bytes"] == 3 * 1024 * 1024


# ---------------------------------------------------------------------------
# Schema validation (_normalize_llm_result)
# ---------------------------------------------------------------------------

def test_normalize_rejects_missing_top_level_field():
    with pytest.raises(GoalInterpretationError):
        _normalize_llm_result({"goal": "x", "target_storage_bytes": 5})


def test_normalize_rejects_negative_target_bytes():
    with pytest.raises(GoalInterpretationError):
        _normalize_llm_result(
            {
                "goal": "x",
                "target_storage_bytes": -5,
                "constraints": {
                    "delete_prohibited": True,
                    "protect_sensitive_data": True,
                    "workspace": None,
                    "approval_required_for": [],
                },
                "strategy": "s",
            }
        )


def test_normalize_rejects_non_list_approval_required_for():
    with pytest.raises(GoalInterpretationError):
        _normalize_llm_result(
            {
                "goal": "x",
                "target_storage_bytes": 5,
                "constraints": {
                    "delete_prohibited": True,
                    "protect_sensitive_data": True,
                    "workspace": None,
                    "approval_required_for": "OVERWRITE",
                },
                "strategy": "s",
            }
        )


def test_normalize_accepts_valid_payload():
    result = _normalize_llm_result(
        {
            "goal": "x",
            "target_storage_bytes": 5,
            "constraints": {
                "delete_prohibited": True,
                "protect_sensitive_data": True,
                "workspace": None,
                "approval_required_for": [],
            },
            "strategy": "s",
        }
    )

    assert result["target_storage_bytes"] == 5
    assert result["constraints"]["delete_prohibited"] is True