from dotenv import load_dotenv
load_dotenv()

from ai.agent import run_ai_mission

final_state = run_ai_mission(
    "Free up 50 KB of storage in big_test_drive, keep everything reversible",
    "demo_data/big_test_drive",
    max_cycles=10,
)

print("Status:", final_state.status)
print("Goal (from LLM):", final_state.user_goal)
print("Constraints:", final_state.constraints)
print("Strategy:", final_state.strategy)
print("Recovered bytes:", final_state.recovered_bytes)