from __future__ import annotations

from collections.abc import Sequence

from retrieval import MovieSearchResult


def build_movie_context(
    movies: Sequence[MovieSearchResult],
    max_overview_chars: int = 700,
) -> str:
    """
    Build a compact, structured text context for the answer-generation LLM.

    The LLM should answer only from this context.
    Therefore, each movie is represented with the most important factual fields
    retrieved from the SQLite database.
    """

    if not movies:
        return "No matching movies were found in the local movie database."

    movie_blocks: list[str] = []

    for index, movie in enumerate(movies, start=1):
        movie_blocks.append(
            _build_single_movie_block(
                index=index,
                movie=movie,
                max_overview_chars=max_overview_chars,
            )
        )

    return "\n\n---\n\n".join(movie_blocks)


def _build_single_movie_block(
    index: int,
    movie: MovieSearchResult,
    max_overview_chars: int,
) -> str:
    return f"""
Movie {index}
Title: {_format_optional(movie.title)}
Year: {_format_optional(movie.year)}
Genres: {_format_optional(movie.genres)}
TMDB rating: {_format_rating(movie.vote_average, movie.vote_count)}
Director: {_format_optional(movie.director)}
Cast: {_format_optional(movie.cast)}
Overview: {_truncate_text(movie.overview, max_overview_chars)}
""".strip()


def _format_optional(value: object | None) -> str:
    if value is None:
        return "Unknown"

    text = str(value).strip()
    return text if text else "Unknown"


def _format_rating(
    vote_average: float | None,
    vote_count: int | None,
) -> str:
    if vote_average is None:
        return "Unknown"

    if vote_count is None:
        return f"{vote_average:.1f}/10"

    return f"{vote_average:.1f}/10 based on {vote_count} votes"


def _truncate_text(value: str | None, max_chars: int) -> str:
    if not value or not value.strip():
        return "No overview available."

    text = " ".join(value.split())

    if len(text) <= max_chars:
        return text

    return text[: max_chars - 3].rstrip() + "..."