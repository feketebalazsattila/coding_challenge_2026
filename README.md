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

The pre-commit hook formats Python files with Ruff, applies safe Ruff fixes,
checks Python syntax, scans for secrets with detect-secrets, and lints YAML and
Markdown files. The commit-msg hook validates commit messages with Commitizen
conventional commits, for example:

```text
feat: add challenge parser
fix: handle empty input
docs: describe setup
```

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
