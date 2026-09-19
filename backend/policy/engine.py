from pathlib import Path

from engines.risk import assess_file_risk
from models.schemes import (
    PolicyDecision,
    POLICY_ALLOW,
    POLICY_DENY,
    POLICY_REQUIRE_APPROVAL,
)


# ---------------------------------------------------------------------------
# Action-type base policy table
# ---------------------------------------------------------------------------
#
# This is the "default conceptual policy" from the architecture doc. It is
# a *starting point* risk classification for an action type in isolation,
# before file-level risk (engines.risk) or operation mode are folded in.

ACTION_BASE_RISK = {
    "READ": "LOW",
    "SCAN": "LOW",
    "CREATE": "LOW",
    "COMPRESS": "LOW",
    "QUARANTINE": "LOW",
    "DUPLICATE_REVIEW": "LOW",
    "MOVE": "MEDIUM",
    "RENAME": "MEDIUM",
    "RESTORE": "MEDIUM",
    "OVERWRITE": "HIGH",
    "DELETE": "HIGH",
    "SENSITIVE_EXPORT": "HIGH",
    "SECRET_EXPOSURE": "HIGH",
}

# Action types that are denied outright regardless of context, unless a
# caller has gone out of their way to mark them explicitly approved
# up-front (mission-level constraint), which this engine still refuses
# to auto-grant - approval for these must come from a human via the
# approval workflow, not from a policy default.
DENY_BY_DEFAULT_ACTIONS = {
    "DELETE",
    "SECRET_EXPOSURE",
}

# Action types that always require human approval before they may run,
# no matter what operation mode the mission is in.
ALWAYS_REQUIRE_APPROVAL_ACTIONS = {
    "OVERWRITE",
    "SENSITIVE_EXPORT",
}


def _action_base_risk(action_type: str) -> str:
    return ACTION_BASE_RISK.get(action_type, "MEDIUM")


def evaluate_action_type(action_type: str) -> PolicyDecision:
    """
    Evaluate an action type in isolation (no file context yet). Useful
    for the Planner to prune obviously-denied action types before doing
    any expensive file-level work.
    """

    risk_level = _action_base_risk(action_type)

    if action_type in DENY_BY_DEFAULT_ACTIONS:
        return PolicyDecision(
            decision=POLICY_DENY,
            reason=(
                f"Action type '{action_type}' is denied by default policy. "
                "Explicit user approval workflow must be used instead of "
                "requesting this action type directly."
            ),
            risk_level=risk_level,
            policy="action_type_default",
            action_type=action_type,
        )

    if action_type in ALWAYS_REQUIRE_APPROVAL_ACTIONS:
        return PolicyDecision(
            decision=POLICY_REQUIRE_APPROVAL,
            reason=(
                f"Action type '{action_type}' always requires explicit "
                "user approval regardless of operation mode."
            ),
            risk_level=risk_level,
            policy="action_type_default",
            action_type=action_type,
        )

    return PolicyDecision(
        decision=POLICY_ALLOW,
        reason=f"Action type '{action_type}' is allowed by default policy.",
        risk_level=risk_level,
        policy="action_type_default",
        action_type=action_type,
    )


def evaluate_file_action(
    action_type: str,
    file_info: dict,
    operation_mode: str,
    approved: bool = False,
) -> PolicyDecision:
    """
    Evaluate a concrete action against a concrete file, combining:

    1. The action-type base policy (evaluate_action_type)
    2. Per-file risk classification (engines.risk.assess_file_risk)
    3. The mission's current operation mode (SAFE / ASK_BEFORE_ACTION /
       AUTONOMOUS)
    4. Whether the action has already been explicitly approved by a
       human (approved=True bypasses an approval requirement, but never
       bypasses an outright DENY)

    This is the same decision logic that used to live inline in
    agent/executor.py's execute_compression(), generalized so any
    domain/tool can reuse it instead of re-implementing the branching.
    """

    path = file_info.get("path", "")

    type_decision = evaluate_action_type(action_type)

    if type_decision.denied:
        return PolicyDecision(
            decision=POLICY_DENY,
            reason=type_decision.reason,
            risk_level=type_decision.risk_level,
            policy=type_decision.policy,
            action_type=action_type,
            path=path,
        )

    file_risk = assess_file_risk(file_info)

    # HIGH-risk files are always protected, no matter the action type or
    # operation mode. This mirrors the original executor.py behaviour
    # exactly (HIGH risk => hard block, full stop).
    if file_risk == "HIGH":
        return PolicyDecision(
            decision=POLICY_DENY,
            reason="HIGH-risk file is protected from modification.",
            risk_level="HIGH",
            policy="file_risk",
            action_type=action_type,
            path=path,
        )

    # An action type that always needs approval (e.g. OVERWRITE) still
    # needs approval even in AUTONOMOUS mode - operation mode can only
    # ever make approval requirements *more* strict for a given file
    # risk, never bypass an action-type-level requirement, unless a
    # human has already approved this exact action.
    if type_decision.requires_approval and not approved:
        return PolicyDecision(
            decision=POLICY_REQUIRE_APPROVAL,
            reason=type_decision.reason,
            risk_level=file_risk,
            policy=type_decision.policy,
            action_type=action_type,
            path=path,
        )

    approval_required = _approval_required_for_mode(
        operation_mode,
        file_risk,
    )

    if approval_required and not approved:
        return PolicyDecision(
            decision=POLICY_REQUIRE_APPROVAL,
            reason=(
                "This action requires explicit user approval in the "
                "current operation mode."
            ),
            risk_level=file_risk,
            policy="operation_mode",
            action_type=action_type,
            path=path,
        )

    return PolicyDecision(
        decision=POLICY_ALLOW,
        reason="Action permitted under current operation mode and risk level.",
        risk_level=file_risk,
        policy="operation_mode",
        action_type=action_type,
        path=path,
    )


def _approval_required_for_mode(operation_mode: str, risk_level: str) -> bool:
    """
    Reproduces the exact operation-mode semantics that previously lived
    in agent/executor.py:

    SAFE_MODE               -> always requires approval
    ASK_BEFORE_ACTION_MODE  -> requires approval only for MEDIUM risk
                               (LOW risk auto-runs, HIGH is already
                               blocked earlier)
    AUTONOMOUS_MODE         -> never requires approval (LOW/MEDIUM run
                               automatically, HIGH is already blocked)
    """

    # Imported lazily to avoid a module-load-order cycle between
    # agent.state and policy.engine (agent.state has no dependency on
    # policy, but keeping the import local here keeps this module
    # importable standalone/tested in isolation too).
    from agent.state import SAFE_MODE, ASK_BEFORE_ACTION_MODE, AUTONOMOUS_MODE

    if operation_mode == SAFE_MODE:
        return True

    if operation_mode == ASK_BEFORE_ACTION_MODE:
        return risk_level == "MEDIUM"

    if operation_mode == AUTONOMOUS_MODE:
        return False

    raise ValueError(f"Unsupported operation mode: {operation_mode}")


def evaluate_path_move(
    source_path: str,
    destination_path: str,
    operation_mode: str,
    approved: bool = False,
) -> PolicyDecision:
    """
    Evaluate a MOVE/RENAME-style action where the destination already
    existing is the primary risk signal (this is the exact scenario the
    Replanner needs to reason about: "destination already exists").
    """

    destination_exists = Path(destination_path).exists()

    if destination_exists:
        return PolicyDecision(
            decision=POLICY_REQUIRE_APPROVAL,
            reason=(
                f"Destination already exists: {destination_path}. "
                "Overwriting requires explicit approval."
            ),
            risk_level="HIGH",
            policy="path_move_overwrite",
            action_type="MOVE",
            path=source_path,
        )

    type_decision = evaluate_action_type("MOVE")

    approval_required = _approval_required_for_mode(
        operation_mode,
        type_decision.risk_level,
    )

    if approval_required and not approved:
        return PolicyDecision(
            decision=POLICY_REQUIRE_APPROVAL,
            reason=(
                "MOVE requires explicit user approval in the current "
                "operation mode."
            ),
            risk_level=type_decision.risk_level,
            policy="operation_mode",
            action_type="MOVE",
            path=source_path,
        )

    return PolicyDecision(
        decision=POLICY_ALLOW,
        reason="Destination is free; move permitted.",
        risk_level=type_decision.risk_level,
        policy="path_move_overwrite",
        action_type="MOVE",
        path=source_path,
    )