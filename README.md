# coding_challenge_2026

## Before You Start

This project uses `uv` for Python package management. If `uv` is not installed,
follow the installation guide below first, then restart your terminal.

## Development

Install the development environment:

```powershell
uv sync --dev
```

Install the Git hooks:

```powershell
uv run pre-commit install --install-hooks
uv run pre-commit install --hook-type commit-msg
```

Run all checks manually:

```powershell
uv run pre-commit run --all-files
```

Run unit tests:

```powershell
uv run pytest
```

The pre-commit hook formats Python files with Ruff, applies safe Ruff fixes,
checks Python syntax, runs unit tests with Pytest, scans for secrets with
detect-secrets, and lints YAML and Markdown files. The commit-msg hook validates
commit messages with Commitizen conventional commits, for example:

```text
feat: add challenge parser
fix: handle empty input
docs: describe setup
```

## Data Setup

Download the TMDB 5000 Movie Dataset CSV files and place them here:

```text
data/tmdb_5000_movies.csv
data/tmdb_5000_credits.csv
```

Or download them with the helper script. The default source is Kaggle through
the Python `kagglehub` package:

```powershell
uv run python scripts/download_data.py
```

Create the local SQLite database:

```powershell
uv run python scripts/setup_data.py --force
```

By default, the setup script reads CSV files from `data/` and creates
`data/movies.sqlite` with `movies`, `genres`, `movie_genres`, and `ratings`
tables. The stored movie fields include title, year, overview/plot, cast, and
director; ratings are stored in the `ratings` table, and genres are normalized
through `movie_genres`.

## Install uv

On Windows PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

On macOS or Linux:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then restart your terminal and check the installation:

```powershell
uv --version
```
