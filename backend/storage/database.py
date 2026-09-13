import json
from pathlib import Path
from typing import Any


DATABASE_FILE = Path(__file__).parent / "synora_state.json"


def save_mission(state: dict[str, Any]) -> None:
    """
    Save mission state to disk.
    """

    DATABASE_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with DATABASE_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            state,
            file,
            indent=4,
        )


def load_mission() -> dict[str, Any] | None:
    """
    Load the saved mission state.

    Returns None if no mission has been saved.
    """

    if not DATABASE_FILE.exists():
        return None

    with DATABASE_FILE.open(
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def clear_mission() -> None:
    """
    Delete the saved mission state.
    """

    if DATABASE_FILE.exists():
        DATABASE_FILE.unlink()