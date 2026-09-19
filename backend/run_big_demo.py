from agent.state import MissionState
from agent.controller import run_mission

state = MissionState(
    mission_id="mission-002",
    user_goal="Recover storage from big_test_drive",
    target_storage_bytes=5000,
)
state.set_operation_mode("AUTONOMOUS")

final_state = run_mission(state, "demo_data/big_test_drive", max_cycles=10)

print("Status:", final_state.status)
print("Recovered bytes:", final_state.recovered_bytes)
print("Completed actions:", len(final_state.completed_actions))
for action in final_state.completed_actions:
    print("  -", action.get("action_type"), action.get("path"), "->", action.get("status"))
print("Verification results:", final_state.verification_results)