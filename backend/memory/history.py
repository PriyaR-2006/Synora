from datetime import datetime, timezone
from typing import Any, Optional

from storage.database import append_history_event, read_history


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record(mission_id: str, event_type: str, data: dict[str, Any]) -> None:
    append_history_event(
        {
            "mission_id": mission_id,
            "event_type": event_type,
            "timestamp": _now_iso(),
            "data": data,
        }
    )


def record_mission_created(mission_id: str, user_goal: str, target_storage_bytes: int) -> None:
    _record(
        mission_id,
        "mission_created",
        {"user_goal": user_goal, "target_storage_bytes": target_storage_bytes},
    )


def record_action_completed(mission_id: str, action: dict[str, Any]) -> None:
    _record(mission_id, "action_completed", {"action": action})


def record_action_failed(mission_id: str, action: dict[str, Any]) -> None:
    _record(mission_id, "action_failed", {"action": action})


def record_approval_requested(mission_id: str, action: dict[str, Any]) -> None:
    _record(mission_id, "approval_requested", {"action": action})


def record_approval_granted(mission_id: str, action: dict[str, Any]) -> None:
    _record(mission_id, "approval_granted", {"action": action})


def record_replan(mission_id: str, original_action: dict[str, Any], alternative_action: Optional[dict[str, Any]]) -> None:
    _record(
        mission_id,
        "replan",
        {"original_action": original_action, "alternative_action": alternative_action},
    )


def record_verification(mission_id: str, verification_result: dict[str, Any]) -> None:
    _record(mission_id, "verification", {"result": verification_result})


def get_mission_history(mission_id: str) -> list[dict[str, Any]]:
    """
    Return every recorded event for a single mission, in the order they
    were recorded.
    """

    return read_history(mission_id=mission_id)


def get_events_by_type(mission_id: str, event_type: str) -> list[dict[str, Any]]:
    return [
        event
        for event in get_mission_history(mission_id)
        if event.get("event_type") == event_type
    ]


def summarize_mission_history(mission_id: str) -> dict[str, Any]:
    """
    Small convenience rollup a future mission (or the API layer) can use
    to get a quick sense of a mission's history without walking the raw
    event list itself.
    """

    events = get_mission_history(mission_id)

    counts: dict[str, int] = {}

    for event in events:
        event_type = event.get("event_type", "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1

    return {
        "mission_id": mission_id,
        "total_events": len(events),
        "counts_by_type": counts,
    }