from agent.state import MissionState
from agent.planner import create_plan


def run_mission(
    state: MissionState,
    directory: str,
) -> MissionState:
    """
    Run one planning step of a Synora mission.
    """

    if state.status == "COMPLETED":
        return state

    state = create_plan(
        state,
        directory,
    )

    return state
    