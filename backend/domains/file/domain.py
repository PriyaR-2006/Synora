from typing import Any

from agent.controller import run_mission
from agent.state import MissionState
from engines.context import build_storage_context
from tools.duplicates import find_duplicates
from tools.registry import default_registry
from workspace.graph import build_graph_from_files


DOMAIN_NAME = "FILE"


def capabilities() -> dict[str, Any]:
    """
    Describe what this domain can currently do. Mirrors the shape
    domains/data and domains/web will eventually return, so the router
    and API layer can treat all domains uniformly.
    """

    return {
        "domain": DOMAIN_NAME,
        "implemented": True,
        "tools": [tool["name"] for tool in default_registry.list_tools()],
        "actions": ["COMPRESS", "DUPLICATE_REVIEW"],
        "description": (
            "Scans a directory, detects duplicates, and safely "
            "compresses+quarantines low/medium-risk files to recover "
            "storage, guided by a goal-driven mission loop."
        ),
    }


def inspect_workspace(directory: str) -> dict[str, Any]:
    """
    Read-only inspection of a directory: storage context + duplicate
    groups + a lightweight workspace graph, without starting a mission.
    Useful for a dashboard/API endpoint that wants to show "what's
    here" before committing to running a mission.
    """

    context = build_storage_context(directory)
    duplicate_groups = find_duplicates(context["files"])
    graph = build_graph_from_files(context["files"])

    return {
        "directory": context["directory"],
        "total_files": context["total_files"],
        "total_size_bytes": context["total_size_bytes"],
        "extensions": context["extensions"],
        "duplicate_group_count": len(duplicate_groups),
        "workspace_graph": graph.to_dict(),
    }


def run(state: MissionState, directory: str, max_cycles: int = 10) -> MissionState:
    """
    Run a mission through the FILE domain. This is a direct passthrough
    to the existing Mission Controller - the FILE domain *is* that
    controller/planner/executor pipeline; this function exists so the
    Domain Router has a uniform `domain.run(state, directory)` interface
    to call regardless of which domain a goal was routed to.
    """

    return run_mission(state, directory, max_cycles=max_cycles)