from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda



clean_yaml_parser = StrOutputParser() | RunnableLambda(lambda x: x.replace("yaml", "").replace("yml", "").replace("```", "").strip())

