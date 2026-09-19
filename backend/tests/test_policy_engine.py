"""
Tests for policy/engine.py.
"""

from models.schemes import POLICY_ALLOW, POLICY_DENY, POLICY_REQUIRE_APPROVAL
from policy.engine import evaluate_action_type, evaluate_file_action, evaluate_path_move


def test_delete_is_denied_by_default():
    decision = evaluate_action_type("DELETE")
    assert decision.decision == POLICY_DENY


def test_read_is_allowed():
    decision = evaluate_action_type("READ")
    assert decision.decision == POLICY_ALLOW


def test_overwrite_always_requires_approval():
    decision = evaluate_action_type("OVERWRITE")
    assert decision.decision == POLICY_REQUIRE_APPROVAL


def test_high_risk_file_denied_even_in_autonomous_mode():
    high_risk_file = {"path": "/tmp/.env", "name": ".env", "size_bytes": 10}

    decision = evaluate_file_action(
        "COMPRESS", high_risk_file, operation_mode="AUTONOMOUS"
    )

    assert decision.decision == POLICY_DENY
    assert decision.risk_level == "HIGH"


def test_safe_mode_requires_approval_for_low_risk_file():
    low_risk_file = {"path": "/tmp/x.txt", "name": "x.txt", "size_bytes": 10}

    decision = evaluate_file_action(
        "COMPRESS", low_risk_file, operation_mode="SAFE"
    )

    assert decision.decision == POLICY_REQUIRE_APPROVAL


def test_autonomous_mode_allows_low_risk_file():
    low_risk_file = {"path": "/tmp/x.txt", "name": "x.txt", "size_bytes": 10}

    decision = evaluate_file_action(
        "COMPRESS", low_risk_file, operation_mode="AUTONOMOUS"
    )

    assert decision.decision == POLICY_ALLOW


def test_approved_flag_bypasses_approval_requirement():
    low_risk_file = {"path": "/tmp/x.txt", "name": "x.txt", "size_bytes": 10}

    decision = evaluate_file_action(
        "COMPRESS", low_risk_file, operation_mode="SAFE", approved=True
    )

    assert decision.decision == POLICY_ALLOW


def test_approved_flag_never_bypasses_deny():
    high_risk_file = {"path": "/tmp/.env", "name": ".env", "size_bytes": 10}

    decision = evaluate_file_action(
        "COMPRESS", high_risk_file, operation_mode="AUTONOMOUS", approved=True
    )

    assert decision.decision == POLICY_DENY


def test_path_move_requires_approval_when_destination_exists(tmp_path):
    destination = tmp_path / "dest.txt"
    destination.write_text("already here")

    decision = evaluate_path_move(
        str(tmp_path / "source.txt"),
        str(destination),
        operation_mode="AUTONOMOUS",
    )

    assert decision.decision == POLICY_REQUIRE_APPROVAL


def test_path_move_allowed_when_destination_free(tmp_path):
    decision = evaluate_path_move(
        str(tmp_path / "source.txt"),
        str(tmp_path / "free_dest.txt"),
        operation_mode="AUTONOMOUS",
    )

    assert decision.decision == POLICY_ALLOW