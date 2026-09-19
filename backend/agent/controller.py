from dataclasses import asdict

from agent.state import MissionState
from agent.planner import create_plan
from agent.executor import execute_compression
from agent.replanner import propose_alternative
from memory import history
from storage.database import save_mission
from verification.verifier import verify_compression_action


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


    if state.status == "CREATED":
        history.record_mission_created(
            state.mission_id,
            state.user_goal,
            state.target_storage_bytes,
        )

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

        # If the replanner proposed a specific alternative action
        # ahead of this planning pass, preserve it the same way an
        # approved action is preserved, so create_plan()'s clear()
        # does not discard it.
        replanner_actions = [
            action
            for action in state.planned_actions
            if action.get("from_replanner") is True
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

        if replanner_actions:
            replanner_paths = {
                action.get("path")
                for action in replanner_actions
            }

            state.planned_actions = [
                action
                for action in state.planned_actions
                if action.get("path") not in replanner_paths
            ]

            state.planned_actions[0:0] = replanner_actions


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

            actions_before = len(state.completed_actions)
            failures_before = len(state.failed_actions)

            state = execute_compression(
                state,
                action,
                compressed_directory,
                approved=action.get("approved", False),
            )

            if len(state.completed_actions) > actions_before:
                history.record_action_completed(
                    state.mission_id,
                    state.completed_actions[-1],
                )
            elif len(state.failed_actions) > failures_before:
                last_failure = state.failed_actions[-1]

                if last_failure.get("status") == "APPROVAL_REQUIRED":
                    history.record_approval_requested(
                        state.mission_id,
                        last_failure,
                    )
                else:
                    history.record_action_failed(
                        state.mission_id,
                        last_failure,
                    )

            # ---------------------------------------------
            # GOAL-LEVEL VERIFICATION (additive, observational)
            # ---------------------------------------------

            if len(state.completed_actions) > actions_before:
                last_action = state.completed_actions[-1]

                verification_result = verify_compression_action(
                    last_action
                )

                state.record_verification(
                    {
                        "action_id": last_action.get("action_id"),
                        "path": last_action.get("path"),
                        "result": verification_result.result,
                        "checks": verification_result.checks,
                        "message": verification_result.message,
                    }
                )

                history.record_verification(
                    state.mission_id,
                    state.verification_results[-1],
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

            # Give the replanner a chance to propose a specific
            # alternative for the most recent failure before falling
            # back to a blind full re-plan next cycle. If it has
            # nothing to offer, this is a no-op and behaviour is
            # identical to the original "clear and re-plan" flow.
            if state.failed_actions:
                last_failure = state.failed_actions[-1]

                alternative = propose_alternative(
                    state,
                    last_failure,
                    directory,
                )

                if alternative is not None:
                    alternative["from_replanner"] = True
                    state.planned_actions.insert(0, alternative)

                    state.record_replan(
                        {
                            "original_action": last_failure,
                            "alternative_action": alternative,
                        }
                    )

                    history.record_replan(
                        state.mission_id,
                        last_failure,
                        alternative,
                    )

            continue


    return state