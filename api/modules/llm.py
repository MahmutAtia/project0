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

# --- Your API keys ---
API_KEYS = [
    os.getenv("GOOGLE_API_KEY"),
    os.getenv("GOOGLE_API_KEY_2"),
    os.getenv("GOOGLE_API_KEY_3"),
    os.getenv("GOOGLE_API_KEY_4"),
]

key_cycle = itertools.cycle([k for k in API_KEYS if k])

def rotating_gemini(input, config=None, **kwargs):
    model = None
    if config and "configurable" in config:
        model = config["configurable"].get("model")

    # shuffle API keys to distribute usage
    random.shuffle(API_KEYS)

    for i, api_key in enumerate(API_KEYS): # directly iterate over the list
        print(f"Trying model={model or 'gemini-2.0-flash'} with key {api_key[-4:]} )", flush=True)

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





