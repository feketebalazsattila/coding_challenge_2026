from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class QueryIntent(str, Enum):
    """Supported high-level movie query intents."""

    MOVIE_LOOKUP = "movie_lookup"
    RECOMMEND_MOVIES = "recommend_movies"
    SEARCH_MOVIES = "search_movies"
    SEARCH_BY_DIRECTOR = "search_by_director"
    SEARCH_BY_ACTOR = "search_by_actor"
    TOP_RATED = "top_rated"
    UNKNOWN = "unknown"


class SortBy(str, Enum):
    """Supported sorting options for movie retrieval."""

    RELEVANCE = "relevance"
    RATING_DESC = "rating_desc"
    YEAR_DESC = "year_desc"
    YEAR_ASC = "year_asc"


class ParsedMovieQuery(BaseModel):
    """
    Structured representation of the user's movie question.

    This model is the contract between:
    - the LLM query parser
    - the SQLite retrieval layer

    The LLM should not generate SQL.
    It should only fill this object.
    """

    model_config = ConfigDict(extra="forbid")

    intent: QueryIntent = Field(
        description="The user's movie-related intent."
    )

    title: str | None = Field(
        default=None,
        description="Specific movie title if the user asks about one movie.",
    )

    genres: list[str] = Field(
        default_factory=list,
        description="Movie genres mentioned by the user, for example Action or Comedy.",
    )

    year: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
        description="Exact release year if the user requested a specific year.",
    )

    year_from: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
        description="Lower release year bound, for example movies after 2010.",
    )

    year_to: int | None = Field(
        default=None,
        ge=1800,
        le=2100,
        description="Upper release year bound, for example movies before 2000.",
    )

    min_rating: float | None = Field(
        default=None,
        ge=0.0,
        le=10.0,
        description="Minimum average rating on a 0-10 TMDB rating scale.",
    )

    director: str | None = Field(
        default=None,
        description="Director name if the user asks for movies by a director.",
    )

    actors: list[str] = Field(
        default_factory=list,
        description="Actor names if the user asks for movies with specific actors.",
    )

    sort_by: SortBy = Field(
        default=SortBy.RELEVANCE,
        description="Sorting strategy for retrieval results.",
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of movies to retrieve.",
    )

    needs_clarification: bool = Field(
        default=False,
        description="True if the query is too vague to retrieve useful results.",
    )

    clarification_question: str | None = Field(
        default=None,
        description="Clarifying question to ask the user if needed.",
    )

    confidence: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Parser confidence between 0 and 1.",
    )