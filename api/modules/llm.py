from langchain_core.runnables import ConfigurableField # for later
from langchain_google_genai import ChatGoogleGenerativeAI



llm_with_alternatives = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash", temperature=0.0, )