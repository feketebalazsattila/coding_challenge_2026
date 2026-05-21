from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from query_processing import ParsedMovieQuery, QueryIntent, SortBy


@dataclass(frozen=True)
class MovieSearchResult:
    id: int
    tmdb_id: int
    title: str
    year: int | None
    overview: str | None
    cast: str | None
    director: str | None
    genres: str
    vote_average: float | None
    vote_count: int | None


class MovieRetriever:
    """
    Retrieves movies from the local SQLite database based on ParsedMovieQuery.

    The LLM does not generate SQL.
    It only produces ParsedMovieQuery.
    This class translates that validated object into a parameterized SQL query.
    """

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection
        self.connection.row_factory = sqlite3.Row

    def search(self, parsed_query: ParsedMovieQuery) -> list[MovieSearchResult]:
        if parsed_query.needs_clarification:
            return []

        if parsed_query.intent == QueryIntent.UNKNOWN:
            return []

        where_clauses: list[str] = []
        params: list[object] = []

        self._add_title_filter(where_clauses, params, parsed_query)
        self._add_year_filters(where_clauses, params, parsed_query)
        self._add_rating_filter(where_clauses, params, parsed_query)
        self._add_director_filter(where_clauses, params, parsed_query)
        self._add_actor_filters(where_clauses, params, parsed_query)
        self._add_genre_filters(where_clauses, params, parsed_query)

        sql = self._build_sql(where_clauses, parsed_query)
        params.append(parsed_query.limit)

        rows = self.connection.execute(sql, params).fetchall()

        return [self._row_to_movie(row) for row in rows]

    def _build_sql(
        self,
        where_clauses: list[str],
        parsed_query: ParsedMovieQuery,
    ) -> str:
        where_sql = ""
        if where_clauses:
            where_sql = "WHERE " + " AND ".join(where_clauses)

        order_by_sql = self._get_order_by_sql(parsed_query)

        return f"""
            SELECT
                m.id,
                m.tmdb_id,
                m.title,
                m.year,
                m.overview,
                m.cast,
                m.director,
                COALESCE(GROUP_CONCAT(g.name, ', '), '') AS genres,
                r.vote_average,
                r.vote_count
            FROM movies AS m
            LEFT JOIN ratings AS r
                ON r.movie_id = m.id
            LEFT JOIN movie_genres AS mg
                ON mg.movie_id = m.id
            LEFT JOIN genres AS g
                ON g.id = mg.genre_id
            {where_sql}
            GROUP BY
                m.id,
                m.tmdb_id,
                m.title,
                m.year,
                m.overview,
                m.cast,
                m.director,
                r.vote_average,
                r.vote_count
            {order_by_sql}
            LIMIT ?
        """

    def _add_title_filter(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        if parsed_query.title:
            where_clauses.append("LOWER(m.title) LIKE LOWER(?) ESCAPE '\\'")
            params.append(self._contains_pattern(parsed_query.title))

    def _add_year_filters(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        if parsed_query.year is not None:
            where_clauses.append("m.year = ?")
            params.append(parsed_query.year)

        if parsed_query.year_from is not None:
            where_clauses.append("m.year >= ?")
            params.append(parsed_query.year_from)

        if parsed_query.year_to is not None:
            where_clauses.append("m.year <= ?")
            params.append(parsed_query.year_to)

    def _add_rating_filter(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        if parsed_query.min_rating is not None:
            where_clauses.append("r.vote_average >= ?")
            params.append(parsed_query.min_rating)

    def _add_director_filter(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        if parsed_query.director:
            where_clauses.append("LOWER(m.director) LIKE LOWER(?) ESCAPE '\\'")
            params.append(self._contains_pattern(parsed_query.director))

    def _add_actor_filters(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        for actor in parsed_query.actors:
            where_clauses.append("LOWER(m.cast) LIKE LOWER(?) ESCAPE '\\'")
            params.append(self._contains_pattern(actor))

    def _add_genre_filters(
        self,
        where_clauses: list[str],
        params: list[object],
        parsed_query: ParsedMovieQuery,
    ) -> None:
        for genre in parsed_query.genres:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM movie_genres AS mg_filter
                    JOIN genres AS g_filter
                        ON g_filter.id = mg_filter.genre_id
                    WHERE mg_filter.movie_id = m.id
                      AND LOWER(g_filter.name) = LOWER(?)
                )
                """
            )
            params.append(genre)

    def _get_order_by_sql(self, parsed_query: ParsedMovieQuery) -> str:
        if parsed_query.sort_by == SortBy.RATING_DESC:
            return "ORDER BY r.vote_average DESC, r.vote_count DESC"

        if parsed_query.sort_by == SortBy.YEAR_DESC:
            return "ORDER BY m.year DESC"

        if parsed_query.sort_by == SortBy.YEAR_ASC:
            return "ORDER BY m.year ASC"

        if parsed_query.intent in {
            QueryIntent.RECOMMEND_MOVIES,
            QueryIntent.TOP_RATED,
        }:
            return "ORDER BY r.vote_average DESC, r.vote_count DESC"

        return "ORDER BY m.title ASC"

    def _row_to_movie(self, row: sqlite3.Row) -> MovieSearchResult:
        return MovieSearchResult(
            id=row["id"],
            tmdb_id=row["tmdb_id"],
            title=row["title"],
            year=row["year"],
            overview=row["overview"],
            cast=row["cast"],
            director=row["director"],
            genres=row["genres"],
            vote_average=row["vote_average"],
            vote_count=row["vote_count"],
        )

    def _contains_pattern(self, value: str) -> str:
        escaped = self._escape_like(value.strip())
        return f"%{escaped}%"

    def _escape_like(self, value: str) -> str:
        return (
            value.replace("\\", "\\\\")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )