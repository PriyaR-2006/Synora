from pathlib import Path
from typing import Optional


class SandboxViolation(ValueError):
    """Raised when a path falls outside the allowed workspace root."""


class Sandbox:
    """
    Represents one allowed workspace root and validates paths against
    it. A mission should construct exactly one Sandbox for its
    directory and route every path through it.
    """

    def __init__(self, workspace_root: str):
        resolved_root = Path(workspace_root).resolve()

        if not resolved_root.exists():
            raise FileNotFoundError(
                f"Workspace root does not exist: {workspace_root}"
            )

        if not resolved_root.is_dir():
            raise NotADirectoryError(
                f"Workspace root is not a directory: {workspace_root}"
            )

        self.root = resolved_root

    def resolve(self, path: str) -> Path:
        """
        Resolve `path` relative to nothing in particular (it may already
        be absolute) and return the fully-resolved Path, without
        checking containment. Use validate() for the containment check.
        """

        return Path(path).resolve()

    def validate(self, path: str) -> Path:
        """
        Resolve `path` and raise SandboxViolation if it falls outside
        the workspace root. Returns the resolved Path on success so
        callers can use it directly.
        """

        resolved = self.resolve(path)

        try:
            is_inside = resolved.is_relative_to(self.root)
        except AttributeError:
            # Python <3.9 fallback (not expected in this environment,
            # kept defensively).
            try:
                resolved.relative_to(self.root)
                is_inside = True
            except ValueError:
                is_inside = False

        if not is_inside:
            raise SandboxViolation(
                f"Path '{path}' resolves to '{resolved}', which is "
                f"outside the allowed workspace root '{self.root}'."
            )

        return resolved

    def is_within(self, path: str) -> bool:
        """
        Non-raising variant of validate(), for callers that want a
        boolean (e.g. a Verifier check) rather than an exception.
        """

        try:
            self.validate(path)
            return True
        except SandboxViolation:
            return False

    def validate_pair(self, source_path: str, destination_path: str) -> tuple[Path, Path]:
        """
        Validate both the source and destination of a move/rename/
        compress-style action. Returns (resolved_source, resolved_dest).
        """

        return self.validate(source_path), self.validate(destination_path)


_active_sandbox: Optional[Sandbox] = None


def set_active_sandbox(sandbox: Optional[Sandbox]) -> None:
    """
    Set (or clear, with None) the process-wide default sandbox. This is
    a convenience for call sites (like the FastAPI layer) that do not
    want to thread a Sandbox instance through every function call.
    Prefer passing a Sandbox explicitly wherever practical - this global
    exists only to keep legacy, non-mission endpoints (e.g. the raw
    /scan, /compress endpoints in api/main.py) safe without a larger
    refactor of their signatures.
    """

    global _active_sandbox
    _active_sandbox = sandbox


def get_active_sandbox() -> Optional[Sandbox]:
    return _active_sandbox


def validate_within_active_sandbox(path: str) -> None:
    """
    If a process-wide sandbox has been configured, validate `path`
    against it. If no sandbox is configured, this is a no-op (so
    existing behaviour for callers that never set one up is unchanged).
    """

    sandbox = get_active_sandbox()

    if sandbox is None:
        return

    sandbox.validate(path)