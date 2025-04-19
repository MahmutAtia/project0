from langchain_core.runnables import ConfigurableField # for later
from langchain_google_genai import ChatGoogleGenerativeAI



llm_with_alternatives = ChatGoogleGenerativeAI(
    model="gemini-2.0-pro-exp-02-05", temperature=1.0
)
