from dataclasses import asdict

from agent.state import MissionState
from agent.planner import create_plan
from agent.executor import execute_compression
from storage.database import save_mission


def run_mission(
    state: MissionState,
    directory: str,
    max_cycles: int = 10,
) -> MissionState:
    """
    Run Synora as a persistent goal-driven agent.

    The agent repeatedly:

    1. Plans
    2. Selects an action
    3. Executes it
    4. Verifies it
    5. Updates state
    6. Saves state
    7. Replans when necessary

    The mission state is saved after every cycle.
    """

    if state.status == "COMPLETED":
        save_mission(asdict(state))
        return state

    state.status = "RUNNING"

    save_mission(
        asdict(state)
    )

    # Keep all agent-generated files inside
    # the same demo storage area used by the
    # Synora dashboard.
    compressed_directory = (
        f"{directory}/compressed"
    )

    for _ in range(max_cycles):

        # ---------------------------------------------
        # CHECK GOAL
        # ---------------------------------------------

        if (
            state.recovered_bytes
            >= state.target_storage_bytes
        ):
            state.status = "COMPLETED"
            state.planned_actions.clear()

            save_mission(
                asdict(state)
            )

            break

        # ---------------------------------------------
        # PLAN
        # ---------------------------------------------

        state = create_plan(
            state,
            directory,
        )

        save_mission(
            asdict(state)
        )

        # ---------------------------------------------
        # NO ACTIONS AVAILABLE
        # ---------------------------------------------

        if not state.planned_actions:

            if (
                state.recovered_bytes
                >= state.target_storage_bytes
            ):
                state.status = "COMPLETED"
            else:
                state.status = "NO_SAFE_ACTIONS"

            save_mission(
                asdict(state)
            )

            break

        # ---------------------------------------------
        # SELECT NEXT ACTION
        # ---------------------------------------------

        action = state.planned_actions.pop(0)

        # ---------------------------------------------
        # EXECUTE
        # ---------------------------------------------

        if action["action_type"] == "COMPRESS":

            state = execute_compression(
                state,
                action,
                compressed_directory,
            )

        elif action["action_type"] == "DUPLICATE_REVIEW":

            # Duplicate review is informational.
            # Synora does not automatically delete
            # duplicate files.
            state.completed_actions.append(
                {
                    "action_type": "DUPLICATE_REVIEW",
                    "keep_path": action["keep_path"],
                    "duplicate_paths": action[
                        "duplicate_paths"
                    ],
                    "duplicate_count": action[
                        "duplicate_count"
                    ],
                    "status": "REVIEW_REQUIRED",
                }
            )

        else:

            state.record_failure(
                {
                    "action_type": action.get(
                        "action_type",
                        "UNKNOWN",
                    ),
                    "path": action.get(
                        "path",
                        "",
                    ),
                    "status": "FAILED",
                    "error": (
                        "Unknown action type."
                    ),
                }
            )

        # ---------------------------------------------
        # SAVE AFTER ACTION
        # ---------------------------------------------

        save_mission(
            asdict(state)
        )

        # ---------------------------------------------
        # GOAL REACHED
        # ---------------------------------------------

        if (
            state.recovered_bytes
            >= state.target_storage_bytes
        ):
            state.status = "COMPLETED"
            state.planned_actions.clear()

            save_mission(
                asdict(state)
            )

            break

        # ---------------------------------------------
        # REPLAN AFTER FAILURE
        # ---------------------------------------------

        if state.status == "REPLANNING":
            continue

    return state