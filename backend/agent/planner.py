from agent.state import MissionState
from engines.context import build_storage_context
from engines.risk import assess_files
from engines.future_value import estimate_files_value
from engines.simulation import simulate_files


def create_plan(
    state: MissionState,
    directory: str,
) -> MissionState:
    """
    Analyze the target directory and create a storage
    optimization plan.
    """

    if state.status == "COMPLETED":
        return state

    state.status = "PLANNING"

    context = build_storage_context(directory)

    files = assess_files(context["files"])
    files = estimate_files_value(files)

    simulations = simulate_files(files)

    # Only consider actions that could actually recover space.
    candidates = [
        simulation
        for simulation in simulations
        if simulation["estimated_recovered_bytes"] > 0
    ]

    # Prefer larger potential savings first.
    candidates.sort(
        key=lambda item: item["estimated_recovered_bytes"],
        reverse=True,
    )

    state.completed_actions.clear()

    for candidate in candidates:
        state.completed_actions.append(
            {
                "action_type": candidate["action_type"],
                "path": candidate["path"],
                "estimated_recovered_bytes":
                    candidate["estimated_recovered_bytes"],
            }
        )

    return state