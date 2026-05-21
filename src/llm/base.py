from typing import Protocol, runtime_checkable

from query_processing import ParsedMovieQuery


class LLMProviderError(RuntimeError):
    """Base exception for LLM provider related errors."""


class QueryParsingError(LLMProviderError):
    """Raised when the LLM query parser cannot produce a valid ParsedMovieQuery."""


class AnswerGenerationError(LLMProviderError):
    """Raised when the LLM answer generator fails."""


@runtime_checkable
class QueryParser(Protocol):
    """
    Interface for components that convert a natural language user message
    into a structured ParsedMovieQuery.

    Example:
        "Recommend high rated action movies after 2010"

    becomes:
        ParsedMovieQuery(
            intent="recommend_movies",
            genres=["Action"],
            year_from=2010,
            min_rating=4.0,
            sort_by="rating_desc",
        )
    """

    async def parse(self, message: str) -> ParsedMovieQuery:
        """Parse a user message into a structured movie query."""


@runtime_checkable
class AnswerGenerator(Protocol):
    """
    Interface for components that generate the final conversational answer.

    This should not retrieve data directly.
    It should only use the provided context.
    """

    async def generate(self, question: str, context: str) -> str:
        """Generate an answer based on the user question and retrieved context."""
