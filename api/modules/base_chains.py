from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableParallel,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

from .llm import llm_with_alternatives
from .helpers import parse_table_info, get_chat_history_messages


class BaseChain:
    """
    BaseChain class to build and manage a chain of components for language processing.
    """


    def __init__(
        self, input_chain=RunnablePassthrough(), output_parser=StrOutputParser()
    ):
        """
        Initializes the BaseChain with the given components, prompt, language model type, and output parser.

        Args:
            input_chain (Runnable, optional): A pre-constructed input chain.
            output_parser (Callable, optional): The output parser to use at the end of the chain (default is StrOutputParser).
        """
        self.input_chain = input_chain
        self.output_parser = output_parser
        self.chain = None

    def build_chain(self, prompt):
        """
        Builds the chain of components, connecting inputs, prompt, language model, and output parser.

        Returns:
            Runnable: The constructed chain.
        """
        llm = llm_with_alternatives
        self.chain = self.input_chain | prompt | llm | self.output_parser
        return self.chain


class SQLChain(BaseChain):
    def __init__(self, output_parser=StrOutputParser()):
        input_components = RunnableParallel(
            {
                "prompt": itemgetter("prompt"),
                "tables": itemgetter("tables"),
                "dialect": itemgetter("engine"),
                "ddl": itemgetter("ddl"),
                "sample_data": itemgetter("sample_data"),
                "chat_history": itemgetter("history"),
            }
        )

        final_input = RunnableParallel(
            {
                "table_info": RunnableLambda(parse_table_info),
                "dialect": itemgetter("dialect"),
                "input": itemgetter("prompt"),
                "chat_history": lambda x: get_chat_history_messages(x["chat_history"]),
            }
        )

        input_chain = input_components | final_input

        super().__init__(input_chain=input_chain, output_parser=output_parser)
