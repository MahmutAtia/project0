from langchain_core.runnables import (
    RunnablePassthrough,
    RunnableParallel,
    RunnableLambda,
)
from langchain_core.output_parsers import StrOutputParser
from operator import itemgetter

from .llm import llm_with_alternatives


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
