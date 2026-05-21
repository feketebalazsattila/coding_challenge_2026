"""Create a local SQLite database from the TMDB 5000 Movie Dataset.

Expected input files:
- tmdb_5000_movies.csv
- tmdb_5000_credits.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from collections.abc import Iterable
from pathlib import Path
from typing import Any

DEFAULT_DATA_DIR = Path("data")
MOVIES_FILE_NAME = "tmdb_5000_movies.csv"
CREDITS_FILE_NAME = "tmdb_5000_credits.csv"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a SQLite database from TMDB 5000 CSV files."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing TMDB CSV files. Default: {DEFAULT_DATA_DIR}",
    )
    parser.add_argument(
        "--movies-csv",
        type=Path,
        help=f"Path to {MOVIES_FILE_NAME}. Default: DATA_DIR/{MOVIES_FILE_NAME}",
    )
    parser.add_argument(
        "--credits-csv",
        type=Path,
        help=f"Path to {CREDITS_FILE_NAME}. Default: DATA_DIR/{CREDITS_FILE_NAME}",
    )
    parser.add_argument(
        "--database",
        type=Path,
        help="SQLite database output path. Default: DATA_DIR/movies.sqlite",
    )
    parser.add_argument(
        "--cast-limit",
        type=int,
        default=5,
        help="Number of main cast members to store per movie. Default: 5",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete the existing database before creating it.",
    )
    return parser.parse_args()


def load_json_list(value: str | None) -> list[dict[str, Any]]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [item for item in parsed if isinstance(item, dict)]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as csv_file:
        return list(csv.DictReader(csv_file))


def get_year(release_date: str | None) -> int | None:
    if not release_date:
        return None
    year_text = release_date.split("-", maxsplit=1)[0]
    return int(year_text) if year_text.isdigit() else None


def get_credit_key(row: dict[str, str]) -> str:
    return row.get("movie_id") or row.get("id") or row.get("title", "")


def build_credits_index(
    rows: Iterable[dict[str, str]], cast_limit: int
) -> dict[str, dict[str, str]]:
    credits: dict[str, dict[str, str]] = {}
    for row in rows:
        cast_names = [
            person.get("name", "")
            for person in load_json_list(row.get("cast"))
            if person.get("name")
        ][:cast_limit]
        directors = [
            person.get("name", "")
            for person in load_json_list(row.get("crew"))
            if person.get("job") == "Director" and person.get("name")
        ]
        credits[get_credit_key(row)] = {
            "cast": ", ".join(cast_names),
            "director": ", ".join(directors),
        }
    return credits


def connect_database(path: Path, force: bool) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    if force and path.exists():
        path.unlink()
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS movies (
            id INTEGER PRIMARY KEY,
            tmdb_id INTEGER NOT NULL UNIQUE,
            title TEXT NOT NULL,
            year INTEGER,
            overview TEXT,
            cast TEXT,
            director TEXT
        );

        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY,
            tmdb_id INTEGER NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS movie_genres (
            movie_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            PRIMARY KEY (movie_id, genre_id),
            FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE,
            FOREIGN KEY (genre_id) REFERENCES genres (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY,
            movie_id INTEGER NOT NULL UNIQUE,
            vote_average REAL,
            vote_count INTEGER,
            FOREIGN KEY (movie_id) REFERENCES movies (id) ON DELETE CASCADE
        );
        """
    )


def reset_data(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DELETE FROM ratings;
        DELETE FROM movie_genres;
        DELETE FROM genres;
        DELETE FROM movies;
        """
    )


def insert_movie(
    connection: sqlite3.Connection,
    row: dict[str, str],
    credits: dict[str, dict[str, str]],
) -> int:
    tmdb_id = int(row["id"])
    credit = credits.get(row["id"]) or credits.get(row.get("title", "")) or {}
    cursor = connection.execute(
        """
        INSERT INTO movies (tmdb_id, title, year, overview, cast, director)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            tmdb_id,
            row.get("title") or row.get("original_title") or "Untitled",
            get_year(row.get("release_date")),
            row.get("overview") or None,
            credit.get("cast") or None,
            credit.get("director") or None,
        ),
    )
    return int(cursor.lastrowid)


def insert_genres(
    connection: sqlite3.Connection,
    movie_id: int,
    genres: list[dict[str, Any]],
) -> None:
    for genre in genres:
        genre_tmdb_id = genre.get("id")
        genre_name = genre.get("name")
        if not isinstance(genre_tmdb_id, int) or not genre_name:
            continue
        connection.execute(
            """
            INSERT INTO genres (tmdb_id, name)
            VALUES (?, ?)
            ON CONFLICT(tmdb_id) DO UPDATE SET name = excluded.name
            """,
            (genre_tmdb_id, genre_name),
        )
        genre_id = connection.execute(
            "SELECT id FROM genres WHERE tmdb_id = ?",
            (genre_tmdb_id,),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT OR IGNORE INTO movie_genres (movie_id, genre_id)
            VALUES (?, ?)
            """,
            (movie_id, genre_id),
        )


def insert_rating(
    connection: sqlite3.Connection,
    movie_id: int,
    row: dict[str, str],
) -> None:
    vote_average = row.get("vote_average")
    vote_count = row.get("vote_count")
    connection.execute(
        """
        INSERT INTO ratings (movie_id, vote_average, vote_count)
        VALUES (?, ?, ?)
        """,
        (
            movie_id,
            float(vote_average) if vote_average else None,
            int(vote_count) if vote_count else None,
        ),
    )


def build_database(
    movies_csv: Path,
    credits_csv: Path,
    database: Path,
    cast_limit: int,
    force: bool,
) -> None:
    if not movies_csv.exists():
        raise FileNotFoundError(f"Movies CSV not found: {movies_csv}")
    if not credits_csv.exists():
        raise FileNotFoundError(f"Credits CSV not found: {credits_csv}")

    movies = read_csv(movies_csv)
    credits = build_credits_index(read_csv(credits_csv), cast_limit)

    with connect_database(database, force) as connection:
        create_schema(connection)
        reset_data(connection)
        for row in movies:
            movie_id = insert_movie(connection, row, credits)
            insert_genres(connection, movie_id, load_json_list(row.get("genres")))
            insert_rating(connection, movie_id, row)

    print(f"Created {database} with {len(movies)} movies.")


def main() -> None:
    args = parse_args()
    movies_csv = args.movies_csv or args.data_dir / MOVIES_FILE_NAME
    credits_csv = args.credits_csv or args.data_dir / CREDITS_FILE_NAME
    database = args.database or args.data_dir / "movies.sqlite"

    build_database(
        movies_csv=movies_csv,
        credits_csv=credits_csv,
        database=database,
        cast_limit=args.cast_limit,
        force=args.force,
    )


if __name__ == "__main__":
    main()
