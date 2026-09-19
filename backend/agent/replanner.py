import re
from pathlib import Path
from typing import Callable, Optional

from agent.state import MissionState


def _versioned_path(path: Path) -> Path:
    """
    Given a path, return the next available "_vN" versioned sibling
    that does not already exist. E.g. report.pdf -> report_v2.pdf ->
    report_v3.pdf, ... This is the general mechanism the architecture
    doc's example ("report_v2.pdf") is one instance of - it works for
    any file, any destination collision, any extension.
    """

    counter = 2

    while True:
        candidate = path.with_name(
            f"{path.stem}_v{counter}{path.suffix}"
        )

        if not candidate.exists():
            return candidate

        counter += 1


def _handle_file_exists_failure(
    state: MissionState,
    failed_action: dict,
    directory: str,
) -> Optional[dict]:
    """
    Handles: FileExistsError-style failures (e.g. compress_file raising
    "Compressed file already exists: ..."), which show up as a FAILED
    action whose error message names an existing destination.

    Strategy: retry the same action_type against a versioned path
    instead of the original destination.
    """

    error_message = failed_action.get("error", "")

    match = re.search(r"already exists: (.+)$", error_message)

    if not match:
        return None

    conflicting_path = Path(match.group(1).strip())

    versioned_destination = _versioned_path(conflicting_path)

    original_path = failed_action.get("path")

    if not original_path:
        return None

    return {
        "action_id": f"replan-{failed_action.get('action_type', 'ACTION')}-{versioned_destination.name}",
        "action_type": failed_action.get("action_type", "COMPRESS"),
        "tool": "compress_file",
        "path": original_path,
        "risk_level": failed_action.get("risk_level", "MEDIUM"),
        "dependencies": [],
        "expected_outcome": (
            f"Action retried against versioned destination "
            f"{versioned_destination.name} to avoid the existing-file "
            f"conflict."
        ),
        "verification_required": True,
        "fallback_strategy": None,
        "replan_reason": (
            f"Original destination '{conflicting_path}' already "
            f"existed; retrying against '{versioned_destination}'."
        ),
    }


def _handle_missing_file_failure(
    state: MissionState,
    failed_action: dict,
    directory: str,
) -> Optional[dict]:
    """
    Handles: the planned file no longer exists (it may have been moved,
    deleted externally, or already quarantined by a prior cycle).

    Strategy: there is no safe alternative action for a file that is
    genuinely gone - the correct move is to drop it, not retry it. This
    handler returns None (defer to the standard "clear and re-plan"
    path) but records why, so the decision is auditable rather than
    silent.
    """

    error_message = failed_action.get("error", "")

    if "does not exist" not in error_message.lower():
        return None

    path = failed_action.get("path")

    if path:
        state.record_replan(
            {
                "original_action": failed_action,
                "alternative_action": None,
                "reason": (
                    f"File '{path}' no longer exists; no safe "
                    f"alternative action - deferring to standard "
                    f"re-plan."
                ),
            }
        )

    return None


# Ordered list of (name, handler) pairs. The first handler that returns
# a non-None alternative wins. Add new handlers here to extend the
# replanner's repertoire without touching the controller.
_FAILURE_HANDLERS: list[tuple[str, Callable[..., Optional[dict]]]] = [
    ("file_exists", _handle_file_exists_failure),
    ("missing_file", _handle_missing_file_failure),
]


def propose_alternative(
    state: MissionState,
    failed_action: dict,
    directory: str,
) -> Optional[dict]:
    """
    Given the most recent failure, try each registered handler in turn
    and return the first concrete alternative action proposed, or None
    if no handler applies (in which case the controller falls back to
    a standard full re-plan, exactly as the original implementation
    always did).

    Only genuine FAILED actions are considered - APPROVAL_REQUIRED and
    BLOCKED are not failures the replanner should try to route around,
    since those require a human decision or reflect an intentional
    policy denial, not a transient/positional failure.
    """

    if failed_action.get("status") != "FAILED":
        return None

    for _name, handler in _FAILURE_HANDLERS:
        alternative = handler(state, failed_action, directory)

        if alternative is not None:
            return alternative

    return None