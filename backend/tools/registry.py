from dataclasses import asdict
from typing import Any, Callable, Optional

from models.schemes import ToolSpec
from security.sandbox import Sandbox, validate_within_active_sandbox

from tools.scanner import scan_directory
from tools.duplicates import find_duplicates
from tools.compression import compress_file
from tools.quarantine import quarantine_file
from tools.restore import restore_file
from tools.verification import calculate_hash, verify_file


class ToolNotFoundError(KeyError):
    """Raised when invoke() is called with an unregistered tool name."""


class Tool:
    """
    One registered tool: metadata (as a ToolSpec) plus the callable that
    actually performs the work. `path_arguments` lists which keyword
    arguments of `execute` are filesystem paths that should be checked
    against the active sandbox before the tool runs.
    """

    def __init__(
        self,
        spec: ToolSpec,
        execute: Callable[..., Any],
        path_arguments: Optional[list[str]] = None,
    ):
        self.spec = spec
        self.execute = execute
        self.path_arguments = path_arguments or []

    def run(self, sandbox: Optional[Sandbox] = None, **kwargs: Any) -> Any:
        for argument_name in self.path_arguments:
            if argument_name not in kwargs:
                continue

            path_value = kwargs[argument_name]

            if sandbox is not None:
                sandbox.validate(path_value)
            else:
                # Fall back to whatever process-wide sandbox (if any)
                # has been configured, so legacy call sites that don't
                # thread a Sandbox through still get *some* protection.
                validate_within_active_sandbox(path_value)

        return self.execute(**kwargs)


class ToolRegistry:
    """
    Holds every registered Tool by name and exposes invoke()/list_tools().
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(
                f"No tool registered with name '{name}'. "
                f"Available tools: {sorted(self._tools)}"
            ) from None

    def invoke(
        self,
        name: str,
        sandbox: Optional[Sandbox] = None,
        **kwargs: Any,
    ) -> Any:
        return self.get(name).run(sandbox=sandbox, **kwargs)

    def list_tools(self) -> list[dict[str, Any]]:
        return [asdict(tool.spec) for tool in self._tools.values()]


# ---------------------------------------------------------------------------
# Register the existing FilePilot tools.
# ---------------------------------------------------------------------------

def _build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()

    registry.register(
        Tool(
            spec=ToolSpec(
                name="scan_directory",
                description=(
                    "Recursively list files under a directory with "
                    "path, name and size_bytes for each."
                ),
                input_schema={"directory": "str"},
                output_schema={"files": "list[dict]"},
                risk_level="LOW",
                permissions=["read"],
            ),
            execute=lambda directory: scan_directory(directory),
            path_arguments=["directory"],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="find_duplicates",
                description=(
                    "Group files by SHA-256 content hash and return "
                    "groups containing more than one file."
                ),
                input_schema={"files": "list[dict]"},
                output_schema={"duplicate_groups": "list[list[dict]]"},
                risk_level="LOW",
                permissions=["read"],
            ),
            execute=lambda files: find_duplicates(files),
            path_arguments=[],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="compress_file",
                description=(
                    "Gzip-compress a file into output_directory as "
                    "<name>.gz. Refuses to overwrite an existing "
                    "compressed file or to re-compress a .gz file."
                ),
                input_schema={
                    "file_path": "str",
                    "output_directory": "str",
                },
                output_schema={"compressed_path": "str"},
                risk_level="LOW",
                permissions=["read", "write"],
            ),
            execute=lambda file_path, output_directory: compress_file(
                file_path, output_directory
            ),
            path_arguments=["file_path", "output_directory"],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="quarantine_file",
                description=(
                    "Move a file into a quarantine directory, avoiding "
                    "collisions by suffixing a counter."
                ),
                input_schema={
                    "file_path": "str",
                    "quarantine_directory": "str",
                },
                output_schema={"quarantine_path": "str"},
                risk_level="MEDIUM",
                permissions=["read", "write", "move"],
            ),
            execute=lambda file_path, quarantine_directory: quarantine_file(
                file_path, quarantine_directory
            ),
            path_arguments=["file_path", "quarantine_directory"],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="restore_file",
                description=(
                    "Move a quarantined file back into a restore "
                    "directory, avoiding collisions by suffixing a "
                    "counter."
                ),
                input_schema={
                    "quarantined_file": "str",
                    "restore_directory": "str",
                },
                output_schema={"restored_path": "str"},
                risk_level="MEDIUM",
                permissions=["read", "write", "move"],
            ),
            execute=lambda quarantined_file, restore_directory: restore_file(
                quarantined_file, restore_directory
            ),
            path_arguments=["quarantined_file", "restore_directory"],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="calculate_hash",
                description="Compute the SHA-256 hash of a file.",
                input_schema={"file_path": "str"},
                output_schema={"hash_value": "str"},
                risk_level="LOW",
                permissions=["read"],
            ),
            execute=lambda file_path: calculate_hash(file_path),
            path_arguments=["file_path"],
        )
    )

    registry.register(
        Tool(
            spec=ToolSpec(
                name="verify_file",
                description=(
                    "Verify that a file's SHA-256 hash matches an "
                    "expected value."
                ),
                input_schema={
                    "file_path": "str",
                    "expected_hash": "str",
                },
                output_schema={"verified": "bool"},
                risk_level="LOW",
                permissions=["read"],
            ),
            execute=lambda file_path, expected_hash: verify_file(
                file_path, expected_hash
            ),
            path_arguments=["file_path"],
        )
    )

    return registry


# Module-level default registry, ready to use without construction
# boilerplate at every call site - mirrors how storage/database.py
# exposes module-level functions rather than requiring a class instance.
default_registry = _build_default_registry()


def invoke(name: str, sandbox: Optional[Sandbox] = None, **kwargs: Any) -> Any:
    return default_registry.invoke(name, sandbox=sandbox, **kwargs)


def list_tools() -> list[dict[str, Any]]:
    return default_registry.list_tools()