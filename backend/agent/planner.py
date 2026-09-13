from pathlib import Path

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

    risk_level = file_info.get("risk_level", "MEDIUM")
    future_value = file_info.get("future_value", 0.5)
    size_bytes = file_info.get("size_bytes", 0)

    # HIGH-risk files must never be planned.
    if risk_level == "HIGH":
        return -1

    # Prefer LOW-risk files over MEDIUM-risk files.
    risk_score = {
        "LOW": 1.0,
        "MEDIUM": 0.4,
    }.get(risk_level, 0.0)

    # Prefer files with lower future value.
    preservation_score = 1.0 - future_value

    # Give larger files a small priority bonus.
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
    Choose which file in a duplicate group should be preserved.

    Higher future-value files are preferred.
    If future value is equal, the larger file is preferred.
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


def create_plan(
    state: MissionState,
    directory: str,
) -> MissionState:
    """
    Create a risk-aware storage optimization plan.

    The planner:

    - Detects duplicate files
    - Protects HIGH-risk files
    - Avoids protected files
    - Avoids successfully completed files
    - Avoids previously failed files
    - Avoids missing files
    - Avoids empty files
    - Uses future value and risk for prioritization
    - Does not automatically delete duplicates
    """

    if state.status == "COMPLETED":
        return state

    state.status = "PLANNING"

    # -------------------------------------------------
    # BUILD STORAGE CONTEXT
    # -------------------------------------------------

    context = build_storage_context(
        directory
    )

    files = assess_files(
        context["files"]
    )

    files = estimate_files_value(
        files
    )

    # -------------------------------------------------
    # BUILD FUTURE-VALUE LOOKUP
    # -------------------------------------------------

    value_by_path = {
        file_info["path"]: file_info[
            "future_value"
        ]
        for file_info in files
    }

    # -------------------------------------------------
    # DUPLICATE DETECTION
    # -------------------------------------------------

    duplicate_groups = find_duplicates(
        files
    )

    duplicate_candidates = []

    for group in duplicate_groups:

        # Ignore groups containing only one usable file.
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

        duplicate_candidates.append(
            {
                "action_type": "DUPLICATE_REVIEW",
                "keep_path": keep_file["path"],
                "duplicate_paths": duplicate_paths,
                "duplicate_count": len(
                    duplicate_paths
                ),
                "reason": (
                    "Identical file contents detected. "
                    "Review duplicate copies before "
                    "any removal."
                ),
            }
        )

    # -------------------------------------------------
    # COMPLETED ACTION HISTORY
    # -------------------------------------------------

    completed_paths = {
        action["path"]
        for action in state.completed_actions
        if action.get("status")
        == "VERIFIED_AND_QUARANTINED"
    }

    # -------------------------------------------------
    # FAILED ACTION HISTORY
    # -------------------------------------------------

    failed_paths = {
        action["path"]
        for action in state.failed_actions
        if action.get("status") in {
            "BLOCKED",
            "APPROVAL_REQUIRED",
            "FAILED",
        }
    }

    # -------------------------------------------------
    # FILTER ELIGIBLE FILES
    # -------------------------------------------------

    eligible_files = []

    for file_info in files:

        file_path = file_info["path"]

        # Protected files are never considered.
        if file_path in state.protected_paths:
            continue

        # Already successfully processed files
        # should not be processed again.
        if file_path in completed_paths:
            continue

        # Previously failed files should not
        # automatically retry.
        if file_path in failed_paths:
            continue

        # File must still exist.
        if not Path(file_path).exists():
            continue

        # Skip empty files.
        if file_info["size_bytes"] <= 0:
            continue

        # HIGH-risk files never enter the plan.
        if file_info.get("risk_level") == "HIGH":
            continue

        eligible_files.append(
            file_info
        )

    # -------------------------------------------------
    # SIMULATE COMPRESSION
    # -------------------------------------------------

    simulations = simulate_files(
        eligible_files
    )

    compression_candidates = []

    for simulation, file_info in zip(
        simulations,
        eligible_files,
    ):

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
                "action_type": simulation[
                    "action_type"
                ],
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
            }
        )

    # -------------------------------------------------
    # PRIORITIZE COMPRESSION ACTIONS
    # -------------------------------------------------

    compression_candidates.sort(
        key=lambda item: item[
            "priority_score"
        ],
        reverse=True,
    )

    # -------------------------------------------------
    # CREATE FINAL PLAN
    # -------------------------------------------------

    state.planned_actions.clear()

    # Compression actions come first because they
    # can directly recover measurable storage.
    for candidate in compression_candidates:
        state.planned_actions.append(
            candidate
        )

    # Duplicate reviews are informational and do
    # not automatically delete anything.
    for duplicate in duplicate_candidates:
        state.planned_actions.append(
            duplicate
        )

    return state