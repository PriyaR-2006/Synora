import json
from pathlib import Path
from typing import Any, Optional


DATABASE_FILE = Path(__file__).parent / "synora_state.json"


def _empty_store() -> dict[str, Any]:
    return {
        "missions": {},
        "latest_mission_id": None,
        "history": [],
    }


def _read_raw() -> dict[str, Any]:
    if not DATABASE_FILE.exists():
        return _empty_store()

    with DATABASE_FILE.open("r", encoding="utf-8") as file:
        try:
            raw = json.load(file)
        except json.JSONDecodeError:
            return _empty_store()

    if not isinstance(raw, dict):
        return _empty_store()

    # Migrate legacy flat-mission format:
    # old files looked like {"mission_id": "...", "status": "...", ...}
    # with no "missions" key at all.
    if "missions" not in raw:
        legacy_mission_id = raw.get("mission_id")

        if legacy_mission_id:
            return {
                "missions": {legacy_mission_id: raw},
                "latest_mission_id": legacy_mission_id,
                "history": [],
            }

        return _empty_store()

    raw.setdefault("missions", {})
    raw.setdefault("latest_mission_id", None)
    raw.setdefault("history", [])

    return raw


def _write_raw(store: dict[str, Any]) -> None:
    DATABASE_FILE.parent.mkdir(parents=True, exist_ok=True)

    with DATABASE_FILE.open("w", encoding="utf-8") as file:
        json.dump(store, file, indent=4)


# ---------------------------------------------------------------------------
# Public API (backward compatible signatures)
# ---------------------------------------------------------------------------

def save_mission(state: dict[str, Any]) -> None:
    """
    Save mission state to disk, keyed by state["mission_id"].

    Also updates latest_mission_id, so load_mission() with no arguments
    keeps returning "the most recently saved mission" as it always did.
    """

    mission_id = state.get("mission_id")

    store = _read_raw()

    if mission_id:
        store["missions"][mission_id] = state
        store["latest_mission_id"] = mission_id
    else:
        # No mission_id present (shouldn't normally happen) - fall back
        # to the old single-slot behaviour so callers never crash.
        store["missions"]["__unkeyed__"] = state
        store["latest_mission_id"] = "__unkeyed__"

    _write_raw(store)


def load_mission(mission_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    """
    Load a mission's saved state.

    - load_mission() with no arguments returns the most recently saved
      mission (old behaviour).
    - load_mission(mission_id="...") returns that specific mission, or
      None if it does not exist.
    """

    store = _read_raw()

    if mission_id is None:
        mission_id = store.get("latest_mission_id")

    if not mission_id:
        return None

    return store["missions"].get(mission_id)


def list_missions() -> list[dict[str, Any]]:
    """
    Return every mission currently stored, most-recently-updated last
    is not guaranteed (dict insertion order), so callers that care about
    recency should sort on a timestamp field of their own.
    """

    store = _read_raw()
    return list(store["missions"].values())


def clear_mission(mission_id: Optional[str] = None) -> None:
    """
    Delete saved mission state.

    - clear_mission() with no arguments wipes the entire store (matches
      the old "delete the single state file" behaviour relied on by
      tests/test_agent.py::test_mission_state_persists).
    - clear_mission(mission_id="...") removes just that mission.
    """

    if mission_id is None:
        if DATABASE_FILE.exists():
            DATABASE_FILE.unlink()
        return

    store = _read_raw()

    store["missions"].pop(mission_id, None)

    if store.get("latest_mission_id") == mission_id:
        store["latest_mission_id"] = None

    _write_raw(store)


# ---------------------------------------------------------------------------
# History log (Memory/History support)
# ---------------------------------------------------------------------------

def append_history_event(event: dict[str, Any]) -> None:
    """
    Append a single event to the durable history log. Used by
    memory/history.py rather than called directly by most code.
    """

    store = _read_raw()
    store["history"].append(event)
    _write_raw(store)


def read_history(mission_id: Optional[str] = None) -> list[dict[str, Any]]:
    """
    Return history events, optionally filtered to a single mission_id.
    """

    store = _read_raw()
    events = store.get("history", [])

    if mission_id is None:
        return events

    return [event for event in events if event.get("mission_id") == mission_id]