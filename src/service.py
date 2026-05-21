from __future__ import annotations

from pydantic import BaseModel, Field

from context_builder import build_movie_context
from llm.base import AnswerGenerator, QueryParser
from query_processing import ParsedMovieQuery
from retrieval import MovieRetriever, MovieSearchResult


class MovieResult(BaseModel):
    id: int
    tmdb_id: int
    title: str
    year: int | None = None
    overview: str | None = None
    cast: str | None = None
    director: str | None = None
    genres: str = ""
    vote_average: float | None = None
    vote_count: int | None = None


class MovieAgentResponse(BaseModel):
    answer: str
    parsed_query: ParsedMovieQuery
    movies: list[MovieResult] = Field(default_factory=list)


class MovieAgentService:
    """
    Coordinates the full movie assistant pipeline.

    Pipeline:
    1. Parse the user message into ParsedMovieQuery using an LLM.
    2. Retrieve matching movies from SQLite using deterministic SQL.
    3. Build a compact movie context.
    4. Generate a conversational answer using a second LLM call.
    """

    def __init__(
        self,
        query_parser: QueryParser,
        retriever: MovieRetriever,
        answer_generator: AnswerGenerator,
    ) -> None:
        self.query_parser = query_parser
        self.retriever = retriever
        self.answer_generator = answer_generator

    async def answer(self, message: str) -> MovieAgentResponse:
        parsed_query = await self.query_parser.parse(message)

        if parsed_query.needs_clarification:
            return MovieAgentResponse(
                answer=(
                    parsed_query.clarification_question
                    or "Could you clarify what kind of movie you are looking for?"
                ),
                parsed_query=parsed_query,
                movies=[],
            )

        movies = self.retriever.search(parsed_query)
        context = build_movie_context(movies)

        answer = await self.answer_generator.generate(
            question=message,
            context=context,
        )

        return MovieAgentResponse(
            answer=answer,
            parsed_query=parsed_query,
            movies=[self._to_movie_result(movie) for movie in movies],
        )

    def _to_movie_result(self, movie: MovieSearchResult) -> MovieResult:
        return MovieResult(
            id=movie.id,
            tmdb_id=movie.tmdb_id,
            title=movie.title,
            year=movie.year,
            overview=movie.overview,
            cast=movie.cast,
            director=movie.director,
            genres=movie.genres,
            vote_average=movie.vote_average,
            vote_count=movie.vote_count,
        )