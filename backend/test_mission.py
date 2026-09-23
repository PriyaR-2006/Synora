from agent.state import MissionState
from agent.controller import run_mission


def main():
    # Point to the folder that has active files waiting for actions
    directory = "demo_data/big_test_drive"

    state = MissionState(
        mission_id="mission-001",
        user_goal="Recover storage safely",
        target_storage_bytes=1,
    )

    final_state = run_mission(
        state,
        directory,
        max_cycles=10,
    )

    print("\n========== SYNORA MISSION ==========")

    print(
        "Mission ID:",
        final_state.mission_id,
    )

    print(
        "Status:",
        final_state.status,
    )

    print(
        "Recovered bytes:",
        final_state.recovered_bytes,
    )

    print(
        "Planned actions:",
        len(final_state.planned_actions),
    )

    print(
        "Completed actions:",
        len(final_state.completed_actions),
    )

    print(
        "Failed actions:",
        len(final_state.failed_actions),
    )

    print(
        "Replanning count:",
        final_state.replanning_count,
    )

    print(
        "Protected paths:",
        len(final_state.protected_paths),
    )

    print("====================================")


if __name__ == "__main__":
    main()