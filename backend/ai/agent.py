from uuid import uuid4
from dataclasses import asdict

from agent.state import MissionState
from agent.controller import run_mission
from ai.reasoning import understand_goal
from storage.database import save_mission


def create_mission_from_request(
    user_request: str,
) -> MissionState:
    """
    Use the AI reasoning layer to convert a natural-language
    request into a Synora MissionState.
    """

    mission = understand_goal(
        user_request
    )

    state = MissionState(
        mission_id=str(uuid4()),
        user_goal=mission["goal"],
        target_storage_bytes=mission[
            "target_storage_bytes"
        ],
    )

    # Store the AI-generated constraints as part
    # of the mission metadata.
    state.planned_actions = []

    save_mission(
        asdict(state)
    )

    return state


def run_ai_mission(
    user_request: str,
    directory: str,
    max_cycles: int = 10,
) -> MissionState:
    """
    Run a complete Synora mission from a natural-language
    user request.

    Flow:

        User request
            ↓
        AI reasoning
            ↓
        MissionState
            ↓
        Deterministic planner
            ↓
        Safe executor
            ↓
        Verification
            ↓
        Persistence
    """

    # ---------------------------------------------
    # UNDERSTAND USER REQUEST
    # ---------------------------------------------

    state = create_mission_from_request(
        user_request
    )

    # ---------------------------------------------
    # RUN EXISTING SYNORA AGENT
    # ---------------------------------------------

    state = run_mission(
        state,
        directory,
        max_cycles=max_cycles,
    )

    return state