import os
from ai.reasoning import _call_grok, DEFAULT_GROK_MODEL

print("Testing Grok connection...")
try:
    result = _call_grok("test request", DEFAULT_GROK_MODEL)
    print("Grok Response Successful:")
    print(result)
except Exception as e:
    print("Error calling Grok:", e)