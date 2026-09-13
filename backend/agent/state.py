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


@dataclass
class MissionState:
    mission_id: str
    user_goal: str
    target_storage_bytes: int

    operation_mode: str = SAFE_MODE

    recovered_bytes: int = 0
    status: str = "CREATED"

    planned_actions: list[dict[str, Any]] = field(default_factory=list)
    completed_actions: list[dict[str, Any]] = field(default_factory=list)
    failed_actions: list[dict[str, Any]] = field(default_factory=list)

    protected_paths: list[str] = field(default_factory=list)

    # Tracks how many times the agent has had to rethink its plan.
    replanning_count: int = 0

    # Tracks actions that should not be blindly retried.
    rejected_actions: list[dict[str, Any]] = field(default_factory=list)

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
            self.status = "WAITING_FOR_APPROVAL"
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
        self.status = "REPLANNING"

    def approve_pending_action(self) -> dict[str, Any]:
        """
        Approve the most recent action that is waiting
        for user approval.

        Returns the approved action so the controller
        can execute it.
        """

        if self.status != "WAITING_FOR_APPROVAL":
            raise ValueError(
                "No action is currently waiting for approval."
            )

        for action in reversed(self.failed_actions):
            if action.get("status") == "APPROVAL_REQUIRED":
                approved_action = dict(action)

                approved_action["approved"] = True

                self.status = "RUNNING"

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
            self.status = "COMPLETED"
            self.planned_actions.clear()
            return True

        return False