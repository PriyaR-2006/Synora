
from dataclasses import dataclass, field
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Pre-existing schemas (kept for backward compatibility)
# ---------------------------------------------------------------------------

@dataclass
class FileCandidate:
    """
    Represents a file that Synora may consider for an action.
    """

    path: str
    size_bytes: int
    reason: str
    risk_level: str = "LOW"
    hash_value: Optional[str] = None


@dataclass
class ActionResult:
    """
    Represents the result of a Synora action.
    """

    success: bool
    action_type: str
    path: str
    storage_recovered_bytes: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# Policy schemas
# ---------------------------------------------------------------------------

# Decision constants (avoid typos scattered across modules).
POLICY_ALLOW = "ALLOW"
POLICY_DENY = "DENY"
POLICY_REQUIRE_APPROVAL = "REQUIRE_APPROVAL"

VALID_POLICY_DECISIONS = {
    POLICY_ALLOW,
    POLICY_DENY,
    POLICY_REQUIRE_APPROVAL,
}


@dataclass
class PolicyDecision:
    """
    The result of evaluating a proposed action against the Policy/Risk
    Engine. Every decision must be explainable: reason + risk_level +
    the policy name that produced it.
    """

    decision: str
    reason: str
    risk_level: str
    policy: str
    action_type: str = ""
    path: str = ""

    def __post_init__(self) -> None:
        if self.decision not in VALID_POLICY_DECISIONS:
            raise ValueError(
                f"Invalid policy decision: {self.decision}. "
                f"Valid decisions are: {sorted(VALID_POLICY_DECISIONS)}"
            )

    @property
    def allowed(self) -> bool:
        return self.decision == POLICY_ALLOW

    @property
    def denied(self) -> bool:
        return self.decision == POLICY_DENY

    @property
    def requires_approval(self) -> bool:
        return self.decision == POLICY_REQUIRE_APPROVAL


# ---------------------------------------------------------------------------
# Tool registry schemas
# ---------------------------------------------------------------------------

@dataclass
class ToolSpec:
    """
    Describes a single registered tool without exposing its execution
    function to callers that only need metadata (e.g. an API listing
    endpoint or a future MCP adapter).
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk_level: str
    permissions: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Planner schemas
# ---------------------------------------------------------------------------

@dataclass
class PlannedAction:
    """
    A single unit of work produced by the Planner.

    This is intentionally a superset of the plain dicts the original
    planner produced (action_type/path/...), so existing dict-based
    consumers (agent/controller.py, agent/executor.py, the tests) keep
    working unchanged. New code can use `to_dict()` and construct plan
    items with the fuller target-architecture shape (dependencies,
    expected_outcome, verification, fallback) when it needs to.
    """

    action_id: str
    action_type: str
    tool: str
    parameters: dict[str, Any] = field(default_factory=dict)
    dependencies: list[str] = field(default_factory=list)
    expected_outcome: str = ""
    risk_level: str = "MEDIUM"
    verification_required: bool = True
    fallback_strategy: Optional[str] = None
    priority_score: float = 0.0

    # Legacy convenience fields mirrored at top-level for the current
    # (dict-shaped) controller/executor, which key off action["path"],
    # action["action_type"], etc. directly.
    path: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "tool": self.tool,
            "parameters": self.parameters,
            "dependencies": self.dependencies,
            "expected_outcome": self.expected_outcome,
            "risk_level": self.risk_level,
            "verification_required": self.verification_required,
            "fallback_strategy": self.fallback_strategy,
            "priority_score": self.priority_score,
            "path": self.path,
        }
        # Merge parameters to top level too, so legacy dict-style access
        # (action["path"], action["keep_path"], ...) keeps working
        # regardless of whether callers read from `parameters` or root.
        merged = dict(self.parameters)
        merged.update(data)
        return merged


# ---------------------------------------------------------------------------
# Verification schemas
# ---------------------------------------------------------------------------

VERIFICATION_PASSED = "PASSED"
VERIFICATION_FAILED = "FAILED"
VERIFICATION_PARTIAL = "PARTIAL"

VALID_VERIFICATION_RESULTS = {
    VERIFICATION_PASSED,
    VERIFICATION_FAILED,
    VERIFICATION_PARTIAL,
}


@dataclass
class VerificationResult:
    """
    Outcome of a goal-level (or action-level) verification check.
    `evidence` is a free-form dict of whatever facts were inspected to
    reach the result, so a human or a later replanning step can see why.
    """

    result: str
    checks: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def __post_init__(self) -> None:
        if self.result not in VALID_VERIFICATION_RESULTS:
            raise ValueError(
                f"Invalid verification result: {self.result}. "
                f"Valid results are: {sorted(VALID_VERIFICATION_RESULTS)}"
            )

    @property
    def passed(self) -> bool:
        return self.result == VERIFICATION_PASSED