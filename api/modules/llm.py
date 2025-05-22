from langchain_core.runnables import ConfigurableField  # for later
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import ConfigurableField



llm_with_alternatives = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
).configurable_fields(
   model =ConfigurableField(
               id="model",
        name="model",
        description="The model to use for the LLM.",
    ),
    # temperature=ConfigurableField(
    #     id="temperature",
    #     description="Controls the randomness of the output. Lower values make the output more deterministic.",
    # ),

)

