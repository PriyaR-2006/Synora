from dataclasses import asdict
import os

from agent.state import MissionState
from agent.planner import create_plan
from agent.executor import execute_compression
# Try importing other executors present in your project
try:
    from agent.executor import execute_quarantine
except ImportError:
    execute_quarantine = None

from agent.replanner import propose_alternative
from memory import history
from storage.database import save_mission
from verification.verifier import verify_compression_action

# Try importing quarantine verifier if present
try:
    from verification.verifier import verify_quarantine_action
except ImportError:
    verify_quarantine_action = None


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
    3. Execute (Compression, Quarantine, Duplicate Review)
    4. Verify
    5. Update state
    6. Save state
    7. Replan if required
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
    save_mission(asdict(state))

    compressed_directory = os.path.join(directory, "compressed")
    quarantine_directory = os.path.join(directory, "quarantine")
    os.makedirs(compressed_directory, exist_ok=True)
    os.makedirs(quarantine_directory, exist_ok=True)

    for cycle in range(max_cycles):

        # ---------------------------------------------
        # CHECK GOAL (Only if explicit target bytes given)
        # ---------------------------------------------
        if state.target_storage_bytes > 0 and state.recovered_bytes >= state.target_storage_bytes:
            state.status = "COMPLETED"
            state.planned_actions.clear()
            save_mission(asdict(state))
            break

        # ---------------------------------------------
        # PRESERVE APPROVED & REPLANNED ACTIONS
        # ---------------------------------------------
        approved_actions = [
            action
            for action in state.planned_actions
            if action.get("approved") is True
        ]

        replanner_actions = [
            action
            for action in state.planned_actions
            if action.get("from_replanner") is True
        ]

        # ---------------------------------------------
        # REBUILD PLAN ONLY IF QUEUE IS EMPTY
        # ---------------------------------------------
        if not state.planned_actions:
            state = create_plan(state, directory)

        if approved_actions:
            approved_paths = {action.get("path") for action in approved_actions}
            state.planned_actions = [
                action for action in state.planned_actions
                if action.get("path") not in approved_paths
            ]
            state.planned_actions[0:0] = approved_actions

        if replanner_actions:
            replanner_paths = {action.get("path") for action in replanner_actions}
            state.planned_actions = [
                action for action in state.planned_actions
                if action.get("path") not in replanner_paths
            ]
            state.planned_actions[0:0] = replanner_actions

        # Clean stale approval errors
        state.failed_actions = [
            action
            for action in state.failed_actions
            if action.get("status") != "APPROVAL_REQUIRED"
        ]

        save_mission(asdict(state))

        # ---------------------------------------------
        # NO ACTIONS AVAILABLE EVALUATION
        # ---------------------------------------------
        if not state.planned_actions:
            if state.completed_actions:
                # If we have already executed actions, the mission succeeded!
                state.status = "COMPLETED"
            elif state.target_storage_bytes > 0 and state.recovered_bytes >= state.target_storage_bytes:
                state.status = "COMPLETED"
            else:
                state.status = "NO_SAFE_ACTIONS"

            save_mission(asdict(state))
            break

        # ---------------------------------------------
        # SELECT ACTION
        # ---------------------------------------------
        action = state.planned_actions.pop(0)
        action_type = action.get("action_type")

        # ---------------------------------------------
        # EXECUTE ACTION & VERIFY
        # ---------------------------------------------
        actions_before = len(state.completed_actions)
        failures_before = len(state.failed_actions)

        if action_type == "COMPRESS":
            state = execute_compression(
                state,
                action,
                compressed_directory,
                approved=action.get("approved", False),
            )

            # Verification for COMPRESS
            if len(state.completed_actions) > actions_before:
                last_action = state.completed_actions[-1]
                verification_result = verify_compression_action(last_action)

                state.record_verification(
                    {
                        "action_id": last_action.get("action_id"),
                        "path": last_action.get("path"),
                        "result": getattr(verification_result, "result", "PASSED"),
                        "checks": getattr(verification_result, "checks", {}),
                        "message": getattr(verification_result, "message", "Verified"),
                    }
                )
                history.record_verification(state.mission_id, state.verification_results[-1])

        elif action_type == "QUARANTINE" and execute_quarantine is not None:
            state = execute_quarantine(
                state,
                action,
                quarantine_directory,
                approved=action.get("approved", False),
            )

            # Verification for QUARANTINE
            if len(state.completed_actions) > actions_before and verify_quarantine_action is not None:
                last_action = state.completed_actions[-1]
                verification_result = verify_quarantine_action(last_action)

                state.record_verification(
                    {
                        "action_id": last_action.get("action_id"),
                        "path": last_action.get("path"),
                        "result": getattr(verification_result, "result", "PASSED"),
                        "checks": getattr(verification_result, "checks", {}),
                        "message": getattr(verification_result, "message", "Quarantine Verified"),
                    }
                )
                history.record_verification(state.mission_id, state.verification_results[-1])

        elif action_type == "DUPLICATE_REVIEW":
            state.completed_actions.append(
                {
                    "action_type": "DUPLICATE_REVIEW",
                    "keep_path": action.get("keep_path"),
                    "duplicate_paths": action.get("duplicate_paths", []),
                    "duplicate_count": action.get("duplicate_count", 0),
                    "status": "REVIEW_REQUIRED",
                }
            )

        else:
            state.record_failure(
                {
                    "action_type": action_type or "UNKNOWN",
                    "path": action.get("path", ""),
                    "status": "FAILED",
                    "error": f"Unsupported action type: {action_type}",
                }
            )

        # ---------------------------------------------
        # RECORD HISTORY METRICS
        # ---------------------------------------------
        if len(state.completed_actions) > actions_before:
            history.record_action_completed(state.mission_id, state.completed_actions[-1])
        elif len(state.failed_actions) > failures_before:
            last_failure = state.failed_actions[-1]
            if last_failure.get("status") == "APPROVAL_REQUIRED":
                history.record_approval_requested(state.mission_id, last_failure)
            else:
                history.record_action_failed(state.mission_id, last_failure)

        save_mission(asdict(state))

        # Check pause
        if state.status == "WAITING_FOR_APPROVAL":
            break

        # ---------------------------------------------
        # REPLAN IF REQUIRED
        # ---------------------------------------------
        if state.status == "REPLANNING" and state.failed_actions:
            last_failure = state.failed_actions[-1]
            alternative = propose_alternative(state, last_failure, directory)
            if alternative is not None:
                alternative["from_replanner"] = True
                state.planned_actions.insert(0, alternative)
                state.record_replan(
                    {
                        "original_action": last_failure,
                        "alternative_action": alternative,
                    }
                )
                history.record_replan(state.mission_id, last_failure, alternative)

    return state