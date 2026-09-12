from dataclasses import dataclass
from typing import Optional


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