from dataclasses import dataclass, field
from typing import Any


SAFE_MODE = "SAFE"
ASK_BEFORE_ACTION_MODE = "ASK_BEFORE_ACTION"
AUTONOMOUS_MODE = "AUTONOMOUS"

VALID_OPERATION_MODES = {
    SAFE_MODE,
    ASK_BEFORE_ACTION_MODE,
    AUTONOMOUS_MODE,
}


# Full target-architecture lifecycle. CREATED, RUNNING, PLANNING,
# WAITING_FOR_APPROVAL, COMPLETED, REPLANNING and NO_SAFE_ACTIONS are the
# original statuses this codebase already used and continues to use
# unchanged. OBSERVING, EXECUTING, VERIFYING, ANALYZING and FAILED are
# additive - existing code never sets them, but new code (verifier,
# replanner) may.
STATUS_CREATED = "CREATED"
STATUS_OBSERVING = "OBSERVING"
STATUS_PLANNING = "PLANNING"
STATUS_WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
STATUS_RUNNING = "RUNNING"
STATUS_EXECUTING = "EXECUTING"
STATUS_VERIFYING = "VERIFYING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"
STATUS_ANALYZING = "ANALYZING"
STATUS_REPLANNING = "REPLANNING"
STATUS_NO_SAFE_ACTIONS = "NO_SAFE_ACTIONS"


@dataclass
class MissionState:
    mission_id: str
    user_goal: str
    target_storage_bytes: int

    operation_mode: str = SAFE_MODE

    recovered_bytes: int = 0
    status: str = STATUS_CREATED

    planned_actions: list[dict[str, Any]] = field(default_factory=list)
    completed_actions: list[dict[str, Any]] = field(default_factory=list)
    failed_actions: list[dict[str, Any]] = field(default_factory=list)

    protected_paths: list[str] = field(default_factory=list)

    # Tracks how many times the agent has had to rethink its plan.
    replanning_count: int = 0

    # Tracks actions that should not be blindly retried.
    rejected_actions: list[dict[str, Any]] = field(default_factory=list)

    # --- Additive fields (Goal Interpreter / Verifier / Replanner) ---

    # Structured constraints produced by ai/reasoning.py, e.g.
    # {"delete_prohibited": True, "workspace": "...", "approval_required": [...]}
    constraints: dict[str, Any] = field(default_factory=dict)

    # Free-text strategy hint produced by ai/reasoning.py.
    strategy: str = ""

    # Directory this mission is scoped to, once known (set by whichever
    # entrypoint creates the mission). Kept optional/blank for missions
    # created the old way that never set it.
    workspace_root: str = ""

    # Goal-level verification results (see verification/verifier.py).
    verification_results: list[dict[str, Any]] = field(default_factory=list)

    # Replanning event log (see agent/replanner.py). Mirrors what gets
    # written to memory/history.py, kept here too for convenience.
    replans: list[dict[str, Any]] = field(default_factory=list)

    def set_operation_mode(self, mode: str) -> None:
        if mode not in VALID_OPERATION_MODES:
            raise ValueError(
                f"Invalid operation mode: {mode}. "
                f"Valid modes are: {sorted(VALID_OPERATION_MODES)}"
            )

        self.operation_mode = mode

    def record_success(self, action: dict[str, Any]) -> None:
        self.completed_actions.append(action)

        self.recovered_bytes += action.get(
            "storage_recovered_bytes",
            0,
        )

        self.check_goal()

    def record_failure(self, action: dict[str, Any]) -> None:
        self.failed_actions.append(action)

        status = action.get("status")

        # Approval is not a failure.
        # The mission should pause until the user approves
        # the pending action.
        if status == "APPROVAL_REQUIRED":
            self.status = STATUS_WAITING_FOR_APPROVAL
            return

        # Remember genuine failures so the planner can avoid
        # blindly selecting the same action again.
        self.rejected_actions.append(
            {
                "action_type": action.get("action_type"),
                "path": action.get("path"),
                "reason": action.get("reason"),
                "status": status,
            }
        )

        self.replanning_count += 1
        self.status = STATUS_REPLANNING

    def approve_pending_action(self) -> dict[str, Any]:
        """
        Approve the most recent action waiting
        for user approval.

        Removes the approval request and places
        the action back into the execution queue.
        """

        if self.status != STATUS_WAITING_FOR_APPROVAL:
            raise ValueError(
                "No action is currently waiting for approval."
            )

        for index in range(
            len(self.failed_actions) - 1,
            -1,
            -1,
        ):
            action = self.failed_actions[index]

            if action.get("status") == "APPROVAL_REQUIRED":
                approved_action = dict(action)

                approved_action["approved"] = True

                # Remove stale approval entry.
                self.failed_actions.pop(index)

                # Put action back into execution queue.
                self.planned_actions.insert(
                    0,
                    approved_action,
                )

                # Continue mission.
                self.status = STATUS_RUNNING

                return approved_action

        raise ValueError(
            "No pending approval action was found."
        )

    def has_failed_path(self, path: str) -> bool:
        """Return True if this path has already failed."""
        return any(
            action.get("path") == path
            for action in self.failed_actions
        )

    def has_rejected_action(
        self,
        action_type: str,
        path: str,
    ) -> bool:
        """Return True if this exact action should not be retried."""
        return any(
            action.get("action_type") == action_type
            and action.get("path") == path
            for action in self.rejected_actions
        )

    def check_goal(self) -> bool:
        if self.recovered_bytes >= self.target_storage_bytes:
            self.status = STATUS_COMPLETED
            self.planned_actions.clear()
            return True

        return False

    def record_verification(self, result: dict[str, Any]) -> None:
        """
        Append a goal-level verification result. Additive - existing
        code never calls this, so it has no effect on old behaviour.
        """

        self.verification_results.append(result)

    def record_replan(self, event: dict[str, Any]) -> None:
        """
        Append a replanning event to the in-memory log. Additive.
        """

        self.replans.append(event)