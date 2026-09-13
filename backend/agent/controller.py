
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

    Flow:
    1. Plan
    2. Select action
    3. Execute
    4. Verify
    5. Update state
    6. Save state
    7. Replan if required

    Human approval pauses the mission safely.
    """

    # Already finished
    if state.status == "COMPLETED":
        save_mission(asdict(state))
        return state

    # Waiting for user approval
    if state.status == "WAITING_FOR_APPROVAL":
        save_mission(asdict(state))
        return state


    state.status = "RUNNING"

    save_mission(
        asdict(state)
    )


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

        # FIX:
        # create_plan() rebuilds planned_actions from
        # scratch (it clears the list), which would
        # otherwise discard any action that was just
        # approved via approve_pending_action() and is
        # sitting at the front of the queue waiting to
        # be executed with approved=True. Preserve those
        # already-approved actions across replanning.

        approved_actions = [
            action
            for action in state.planned_actions
            if action.get("approved") is True
        ]

        state = create_plan(
            state,
            directory,
        )

        if approved_actions:
            approved_paths = {
                action.get("path")
                for action in approved_actions
            }

            state.planned_actions = [
                action
                for action in state.planned_actions
                if action.get("path") not in approved_paths
            ]

            state.planned_actions[0:0] = approved_actions


        # FIX:
        # Remove stale approval errors.
        # Otherwise every approval creates duplicates.

        state.failed_actions = [
            action
            for action in state.failed_actions
            if action.get("status")
            != "APPROVAL_REQUIRED"
        ]


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
        # SELECT ACTION
        # ---------------------------------------------

        action = state.planned_actions.pop(0)



        # ---------------------------------------------
        # EXECUTE ACTION
        # ---------------------------------------------

        if action["action_type"] == "COMPRESS":

            state = execute_compression(
                state,
                action,
                compressed_directory,
                approved=action.get("approved", False),
            )


        elif action["action_type"] == "DUPLICATE_REVIEW":


            state.completed_actions.append(
                {
                    "action_type": "DUPLICATE_REVIEW",

                    "keep_path": action[
                        "keep_path"
                    ],

                    "duplicate_paths": action[
                        "duplicate_paths"
                    ],

                    "duplicate_count": action[
                        "duplicate_count"
                    ],

                    "status":
                        "REVIEW_REQUIRED",
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

                    "status":
                        "FAILED",

                    "error":
                        "Unknown action type.",
                }
            )



        # ---------------------------------------------
        # SAVE
        # ---------------------------------------------

        save_mission(
            asdict(state)
        )



        # ---------------------------------------------
        # WAIT APPROVAL
        # ---------------------------------------------

        if state.status == "WAITING_FOR_APPROVAL":

            break



        # ---------------------------------------------
        # GOAL COMPLETE
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
        # REPLAN
        # ---------------------------------------------

        if state.status == "REPLANNING":

            continue



    return state