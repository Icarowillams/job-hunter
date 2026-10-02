# Repository Guidelines

## Project Structure

This is a Python Job Hunter application (Python 3.11+). Production code is in `src/`, organized into `domain/`, `application/`, `infrastructure/`, `ingestion/`, `analysis/`, `extraction/`, `matching/`, `scoring/`, and `pipeline/`. Tests are in `tests/unit/` and use pytest. Windows setup and scheduling helpers are in `windows/`. Local configuration uses `config.yaml` and `.env.example`; the README and Windows guides cover setup and usage.

## Development and Tests

Use the existing virtual environment for Python commands. On Windows, run the application with `.venv\Scripts\python.exe -m src.main`. Run focused tests first, for example `.venv\Scripts\python.exe -m pytest tests/unit/test_requirement_extractor.py`; run the full suite with `.venv\Scripts\python.exe -m pytest` before declaring a task complete. For behavior changes, add or update focused pytest coverage. Use the existing development tools (Black, isort, Flake8, mypy) where relevant; avoid broad formatting changes.

## Code and Change Conventions

Follow the existing architecture and Python style: four-space indentation, `snake_case` modules and functions, and `PascalCase` classes. Inspect the implementation and its tests before editing. Keep changes small and task-focused, and do not modify unrelated files. Use conventional commit prefixes (`fix:`, `feat:`, `docs:`, `test:`, `refactor:`) when asked to propose a commit message. Never commit or push without explicit approval; leave all Git actions for the user.

## Job Data and Matching Rules

Keep rule-based requirement extraction conservative: mark a requirement mandatory only when the text provides sufficient contextual evidence. Preserve the distinction between Java and JavaScript as separate skills. Do not alter a candidate profile to inflate compatibility scores. For bug fixes, explain the root cause and verify the correction with tests. Preserve functionality; never delete files or behavior unless explicitly requested.

## Local Data and Secrets

Never read out, print, expose, commit, or push secrets from `.env`. Do not modify `README.md` during routine work. Do not change `data/`, `reports/`, `logs/`, or other local runtime artifacts unless the task explicitly requires it. Keep credentials, personal data, and generated output out of commits.
