"""Download the TMDB 5000 Movie Dataset into the local data folder."""

from __future__ import annotations

import argparse
import shutil
import urllib.request
import zipfile
from pathlib import Path

DEFAULT_DATASET = "tmdb/tmdb-movie-metadata"
DEFAULT_OUTPUT_DIR = Path("data")
EXPECTED_FILES = ("tmdb_5000_movies.csv", "tmdb_5000_credits.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download TMDB 5000 Movie Dataset CSV files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory for downloaded CSV files. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--dataset",
        default=DEFAULT_DATASET,
        help=f"Kaggle dataset slug. Default: {DEFAULT_DATASET}",
    )
    parser.add_argument(
        "--zip-url",
        help="Optional direct URL to a ZIP file containing the TMDB CSV files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Download again even if both expected CSV files already exist.",
    )
    return parser.parse_args()


def expected_paths(output_dir: Path) -> list[Path]:
    return [output_dir / file_name for file_name in EXPECTED_FILES]


def has_expected_files(output_dir: Path) -> bool:
    return all(path.exists() for path in expected_paths(output_dir))


def download_with_kagglehub(dataset: str, output_dir: Path) -> None:
    try:
        import kagglehub
    except ImportError as error:
        raise RuntimeError(
            "kagglehub is not installed. Run `uv sync`, then try again."
        ) from error

    download_path = Path(kagglehub.dataset_download(dataset))
    for file_name in EXPECTED_FILES:
        source = download_path / file_name
        if source.exists():
            shutil.copy2(source, output_dir / file_name)


def download_with_url(zip_url: str, output_dir: Path) -> None:
    zip_path = output_dir / "tmdb_5000_movie_dataset.zip"
    urllib.request.urlretrieve(zip_url, zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(output_dir)
    zip_path.unlink()


def validate_download(output_dir: Path) -> None:
    missing_files = [
        path.name for path in expected_paths(output_dir) if not path.exists()
    ]
    if missing_files:
        missing = ", ".join(missing_files)
        raise FileNotFoundError(f"Download finished, but missing files: {missing}")


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if has_expected_files(args.output_dir) and not args.force:
        print(
            f"Dataset already exists in {args.output_dir}. Use --force to redownload."
        )
        return

    if args.zip_url:
        download_with_url(args.zip_url, args.output_dir)
    else:
        download_with_kagglehub(args.dataset, args.output_dir)

    validate_download(args.output_dir)
    print(f"Downloaded TMDB 5000 CSV files to {args.output_dir}.")


if __name__ == "__main__":
    main()
