from __future__ import annotations

import csv
import shutil
import sqlite3
import uuid
from pathlib import Path

from scripts.setup_data import build_database


def write_csv(path, fieldnames, rows) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_build_database_creates_expected_sqlite_tables() -> None:
    work_dir = Path(".test_tmp") / uuid.uuid4().hex
    work_dir.mkdir(parents=True)
    try:
        movies_csv = work_dir / "tmdb_5000_movies.csv"
        credits_csv = work_dir / "tmdb_5000_credits.csv"
        database = work_dir / "movies.sqlite"

        write_csv(
            movies_csv,
            [
                "id",
                "title",
                "original_title",
                "release_date",
                "genres",
                "overview",
                "vote_average",
                "vote_count",
            ],
            [
                {
                    "id": "10",
                    "title": "Example Movie",
                    "original_title": "Example Movie",
                    "release_date": "2001-04-05",
                    "genres": (
                        '[{"id": 18, "name": "Drama"}, {"id": 35, "name": "Comedy"}]'
                    ),
                    "overview": "A small example plot.",
                    "vote_average": "7.2",
                    "vote_count": "123",
                }
            ],
        )
        write_csv(
            credits_csv,
            ["movie_id", "title", "cast", "crew"],
            [
                {
                    "movie_id": "10",
                    "title": "Example Movie",
                    "cast": '[{"name": "Actor One"}, {"name": "Actor Two"}]',
                    "crew": (
                        '[{"job": "Director", "name": "Director One"}, '
                        '{"job": "Producer", "name": "Producer One"}]'
                    ),
                }
            ],
        )

        build_database(
            movies_csv=movies_csv,
            credits_csv=credits_csv,
            database=database,
            cast_limit=1,
            force=True,
        )

        with sqlite3.connect(database) as connection:
            movie = connection.execute(
                """
                SELECT tmdb_id, title, year, overview, "cast", director
                FROM movies
                """
            ).fetchone()
            rating = connection.execute(
                """
                SELECT vote_average, vote_count
                FROM ratings
                """
            ).fetchone()
            genres = connection.execute(
                """
                SELECT genres.name
                FROM genres
                JOIN movie_genres ON movie_genres.genre_id = genres.id
                JOIN movies ON movies.id = movie_genres.movie_id
                WHERE movies.tmdb_id = 10
                ORDER BY genres.name
                """
            ).fetchall()

        assert movie == (
            10,
            "Example Movie",
            2001,
            "A small example plot.",
            "Actor One",
            "Director One",
        )
        assert rating == (7.2, 123)
        assert genres == [("Comedy",), ("Drama",)]
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
