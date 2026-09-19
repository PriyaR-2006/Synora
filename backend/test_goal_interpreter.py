from dotenv import load_dotenv
load_dotenv()

from ai.reasoning import understand_goal
import json

result = understand_goal("Free up 50 MB of storage in ./big_test_drive without deleting anything")
print(json.dumps(result, indent=2))