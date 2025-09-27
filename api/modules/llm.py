import logging
import os
import itertools
from google.api_core.exceptions import ResourceExhausted
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableLambda

from langchain_google_genai import chat_models as cg
import random



# Prevent automatic retries in the Google Gemini client
_original_chat_with_retry = cg._chat_with_retry

def _no_retry(*args, **kwargs):
    # Remove max_retries if it exists in kwargs
    kwargs.pop('max_retries', None) 
    
    # Force max_retries=0 by explicitly passing it now
    # Since it's no longer in kwargs, this is safe.
    return _original_chat_with_retry(*args, max_retries=0, **kwargs)

cg._chat_with_retry = _no_retry

# --- Log configuration to suppress LangChain warnings ---
# Get the logger for the specific library

# Set the logging level to ERROR or CRITICAL to hide WARNINGS
# logging.ERROR will show only errors and critical messages
# logging.CRITICAL will show only critical messages

# --- 1. Load your API keys from environment variables ---
API_KEYS = [
    os.getenv("GOOGLE_API_KEY"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
]

# --- 2. Create a stateful, cycling iterator for the keys ---
# This filters out any empty/None keys and is created only ONCE when the app starts.
VALID_KEYS = [key for key in API_KEYS if key]
if not VALID_KEYS:
    raise ValueError("No valid Google API keys found in environment variables.")
    
key_cycle = itertools.cycle(VALID_KEYS)

def rotating_gemini(input, config=None, **kwargs):
    model = None
    if config and "configurable" in config:
        model = config["configurable"].get("model")

    for _ in range(len(VALID_KEYS)):
        try:
            # Get the next key from our global cycle
            current_key = next(key_cycle)
            print(f"Trying model='{model or 'gemini-2.0-flash'}' with key ending in ...{current_key[-4:]}", flush=True)


            llm = ChatGoogleGenerativeAI(
                model=model or "gemini-2.0-flash",
                google_api_key=current_key,
            )
            return llm.invoke(input, config=config, **kwargs)

        except Exception as e:
            # --- 5. If ANY error occurs, log it and try the next key ---
            # This broad exception catches rate limits, invalid keys, network issues, etc.
            print(f"⚠️ Key ...{current_key[-4:]} failed. Reason: {type(e).__name__}. Trying next key.", flush=True)
            # The 'continue' statement moves to the next iteration of the for-loop
            continue
    # This line is only reached if all keys in the list have failed
    raise RuntimeError("All API keys failed.")

# --- Wrap in RunnableLambda ---
rotating_llm = RunnableLambda(rotating_gemini)





