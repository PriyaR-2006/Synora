
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MissionState:
    """
    Stores the current state of a Synora mission.
    """

    mission_id: str
    user_goal: str
    target_storage_bytes: int

    recovered_bytes: int = 0
    status: str = "CREATED"

    planned_actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    completed_actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    failed_actions: list[dict[str, Any]] = field(
        default_factory=list
    )

    protected_paths: list[str] = field(
        default_factory=list
    )

    replanning_count: int = 0

    def record_success(self, action: dict[str, Any]) -> None:
        """
        Record a successfully completed action.
        """

        self.completed_actions.append(action)

        self.recovered_bytes += action.get(
            "storage_recovered_bytes",
            0,
        )

        self.check_goal()

    def record_failure(self, action: dict[str, Any]) -> None:
        """
        Record a failed action.
        """

        self.failed_actions.append(action)

        self.replanning_count += 1

        self.status = "REPLANNING"

    def check_goal(self) -> bool:
        """
        Check whether the storage goal has been achieved.
        """

        if self.recovered_bytes >= self.target_storage_bytes:
            self.status = "COMPLETED"

            # No remaining actions are needed once
            # the storage goal has been achieved.
            self.planned_actions.clear()

            return True

        return False