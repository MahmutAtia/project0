import logging
import os
import itertools
from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableLambda

from langchain_google_genai import chat_models as cg

# Save original
_original_chat_with_retry = cg._chat_with_retry

def _no_retry(*args, **kwargs):
    # Force max_retries=0
    return _original_chat_with_retry(*args, max_retries=0, **kwargs)

cg._chat_with_retry = _no_retry

# --- Log configuration to suppress LangChain warnings ---
# Get the logger for the specific library

# Set the logging level to ERROR or CRITICAL to hide WARNINGS
# logging.ERROR will show only errors and critical messages
# logging.CRITICAL will show only critical messages

# --- Your API keys ---
API_KEYS = [
    os.getenv("GOOGLE_API_KEY"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
]

print(f"Loaded {API_KEYS} API keys.")   
key_cycle = itertools.cycle([k for k in API_KEYS if k])

def rotating_gemini(input, config=None, **kwargs):
    model = None
    if config and "configurable" in config:
        model = config["configurable"].get("model")

    for i, api_key in enumerate(API_KEYS): # directly iterate over the list
        print(f"Trying model={model or 'gemini-2.0-flash'} with key {i+1}", flush=True)

        if not api_key:
            print(f"⚠️ Skipping empty key at position {i+1}", flush=True)
            continue

        llm = ChatGoogleGenerativeAI(
            model=model or "gemini-2.0-flash",
            google_api_key=api_key,
        )
        try:
            return llm.invoke(input, config=config, **kwargs)

        except Exception as e:
            print(f"⚠️ Error with key {i+1} key:{api_key[-4:]}", flush=True)
            print(f"   Error details: {e}", flush=True)  
            # The 'continue' statement here will automatically move to the next key in the loop
            continue

    # This line is only reached if all keys in the list have failed
    raise RuntimeError("All API keys failed.")

# --- Wrap in RunnableLambda ---
rotating_llm = RunnableLambda(rotating_gemini)





# # just give one key for now
# def rotating_gemini(input, config=None, **kwargs):
#     model = None
#     if config and "configurable" in config:
#         model = config["configurable"].get("model")
    
#     api_key = "AIzaSyD0lTb6o6aQ9UVo4fbC0g3KFBBEB2D2zeU"
#     return ChatGoogleGenerativeAI(
#         model=model or "gemini-2.0-flash",
#         google_api_key=api_key,
#     ).invoke(input, config=config, **kwargs)
# rotating_llm = RunnableLambda(rotating_gemini)
