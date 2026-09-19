from dotenv import load_dotenv
load_dotenv()

from ai.reasoning import _call_openai, DEFAULT_OPENAI_MODEL

result = _call_openai("test request", DEFAULT_OPENAI_MODEL)
print(result)