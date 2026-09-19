from pathlib import Path
from uuid import uuid4

from agent.state import MissionState
from engines.context import build_storage_context
from engines.risk import assess_files
from engines.future_value import estimate_files_value
from engines.simulation import simulate_files
from tools.duplicates import find_duplicates


def calculate_action_score(file_info: dict) -> float:
    """
    Calculate how suitable a file is for automatic compression.

    Higher scores indicate better candidates.
    """

    risk_level = file_info.get(
        "risk_level",
        "MEDIUM",
    )

    future_value = file_info.get(
        "future_value",
        0.5,
    )

    size_bytes = file_info.get(
        "size_bytes",
        0,
    )

    # HIGH-risk files must never be planned.
    if risk_level == "HIGH":
        return -1

    risk_score = {
        "LOW": 1.0,
        "MEDIUM": 0.4,
    }.get(
        risk_level,
        0.0,
    )

    preservation_score = (
        1.0 - future_value
    )

    size_score = min(
        size_bytes / 1_000_000,
        10,
    )

    return (
        risk_score * 100
        + preservation_score * 50
        + size_score
    )


def choose_duplicate_to_keep(
    duplicate_group: list[dict],
    value_by_path: dict[str, float],
) -> dict:
    """
    Choose which file in a duplicate group
    should be preserved.
    """

    return max(
        duplicate_group,
        key=lambda file_info: (
            value_by_path.get(
                file_info["path"],
                0.5,
            ),
            file_info["size_bytes"],
        ),
    )


def _new_action_id() -> str:
    return f"action-{uuid4().hex[:12]}"


def create_plan(
    state: MissionState,
    directory: str,
) -> MissionState:
    """
    Create a risk-aware storage optimization plan.

    The planner:

    - Detects duplicate files
    - Avoids repeating completed duplicate reviews
    - Calculates potential duplicate recovery
    - Protects HIGH-risk files
    - Avoids protected files
    - Avoids successfully completed files
    - Avoids genuinely failed files
    - Allows approval-required actions to be reconsidered
    - Avoids missing files
    - Avoids empty files
    - Avoids unprofitable compression
    - Uses future value and risk for prioritization
    - Does not automatically delete duplicates
    - Honors mission constraints from the Goal Interpreter (e.g. a
      delete_prohibited constraint is always true for this planner
      already, since it never plans DELETE actions at all - the field
      is read here defensively so a future domain/action type can act
      on it without the planner needing to change shape again)
    """

    if state.status == "COMPLETED":
        return state

    state.status = "PLANNING"

    # --------------------------------------------------
    # BUILD STORAGE CONTEXT
    # --------------------------------------------------

    context = build_storage_context(
        directory
    )

    files = assess_files(
        context["files"]
    )

    files = estimate_files_value(
        files
    )

    value_by_path = {
        file_info["path"]: file_info[
            "future_value"
        ]
        for file_info in files
    }

    duplicate_groups = find_duplicates(
        files
    )

    # --------------------------------------------------
    # DUPLICATE REVIEW HISTORY
    # --------------------------------------------------

    reviewed_duplicate_pairs = set()

    for action in state.completed_actions:

        if action.get("action_type") != (
            "DUPLICATE_REVIEW"
        ):
            continue

        keep_path = action.get(
            "keep_path"
        )

        duplicate_paths = action.get(
            "duplicate_paths",
            [],
        )

        if not keep_path:
            continue

        for duplicate_path in duplicate_paths:

            pair = tuple(
                sorted(
                    [
                        keep_path,
                        duplicate_path,
                    ]
                )
            )

            reviewed_duplicate_pairs.add(
                pair
            )

    duplicate_candidates = []

    for group in duplicate_groups:

        if len(group) < 2:
            continue

        keep_file = choose_duplicate_to_keep(
            group,
            value_by_path,
        )

        duplicate_paths = [
            file_info["path"]
            for file_info in group
            if file_info["path"]
            != keep_file["path"]
        ]

        # Check whether this duplicate group
        # has already been reviewed.
        already_reviewed = True

        for duplicate_path in duplicate_paths:

            pair = tuple(
                sorted(
                    [
                        keep_file["path"],
                        duplicate_path,
                    ]
                )
            )

            if pair not in reviewed_duplicate_pairs:
                already_reviewed = False
                break

        if already_reviewed:
            continue

        potential_recovered_bytes = sum(
            file_info["size_bytes"]
            for file_info in group
            if file_info["path"]
            != keep_file["path"]
        )

        duplicate_candidates.append(
            {
                "action_id": _new_action_id(),
                "action_type": "DUPLICATE_REVIEW",
                "tool": "find_duplicates",
                "keep_path": keep_file["path"],
                "duplicate_paths": duplicate_paths,
                "duplicate_count": len(
                    duplicate_paths
                ),
                "potential_recovered_bytes": (
                    potential_recovered_bytes
                ),
                "dependencies": [],
                "expected_outcome": (
                    "User reviews duplicate copies; no file is "
                    "deleted automatically."
                ),
                "risk_level": "LOW",
                "verification_required": False,
                "fallback_strategy": None,
                "reason": (
                    "Identical file contents detected. "
                    "Review duplicate copies before "
                    "any removal."
                ),
            }
        )

    # --------------------------------------------------
    # COMPLETED / FAILED PATHS
    # --------------------------------------------------

    completed_paths = {
        action["path"]
        for action in state.completed_actions
        if action.get("status")
        == "VERIFIED_AND_QUARANTINED"
    }

    # IMPORTANT:
    # APPROVAL_REQUIRED is intentionally NOT included
    # here. A file waiting for approval should remain
    # eligible once the user approves it.
    failed_paths = {
        action["path"]
        for action in state.failed_actions
        if action.get("status") in {
            "BLOCKED",
            "FAILED",
        }
    }

    # --------------------------------------------------
    # ELIGIBLE COMPRESSION FILES
    # --------------------------------------------------

    eligible_files = []

    for file_info in files:

        file_path = file_info["path"]

        if file_path in state.protected_paths:
            continue

        if file_path in completed_paths:
            continue

        if file_path in failed_paths:
            continue

        if not Path(file_path).exists():
            continue

        if file_info["size_bytes"] <= 0:
            continue

        if file_info.get("risk_level") == "HIGH":
            continue

        eligible_files.append(
            file_info
        )

    # --------------------------------------------------
    # SIMULATION
    # --------------------------------------------------

    simulations = simulate_files(
        eligible_files
    )

    compression_candidates = []

    for simulation, file_info in zip(
        simulations,
        eligible_files,
    ):

        # Ignore simulations that do not actually
        # recover storage.
        if not simulation.get(
            "profitable",
            False,
        ):
            continue

        estimated_recovered = (
            simulation[
                "estimated_recovered_bytes"
            ]
        )

        if estimated_recovered <= 0:
            continue

        score = calculate_action_score(
            file_info
        )

        if score < 0:
            continue

        compression_candidates.append(
            {
                "action_id": _new_action_id(),
                "action_type": simulation[
                    "action_type"
                ],
                "tool": "compress_file",
                "path": simulation[
                    "path"
                ],
                "estimated_recovered_bytes": (
                    estimated_recovered
                ),
                "risk_level": file_info[
                    "risk_level"
                ],
                "future_value": file_info[
                    "future_value"
                ],
                "priority_score": score,
                "dependencies": [],
                "expected_outcome": (
                    f"File compressed and original quarantined; "
                    f"~{estimated_recovered} bytes recovered."
                ),
                "verification_required": True,
                "fallback_strategy": (
                    "If the destination already exists, retry with "
                    "a versioned filename."
                ),
            }
        )

    # Highest-priority compression candidates first.
    compression_candidates.sort(
        key=lambda item: item[
            "priority_score"
        ],
        reverse=True,
    )

    # --------------------------------------------------
    # FINAL PLAN
    # --------------------------------------------------

    state.planned_actions.clear()

    # Compression actions are placed first so the
    # mission can recover real storage before handling
    # informational duplicate reviews.
    for candidate in compression_candidates:

        state.planned_actions.append(
            candidate
        )

    # Duplicate review is informational only.
    # It never automatically deletes a file.
    for duplicate in duplicate_candidates:

        state.planned_actions.append(
            duplicate
        )

    return state