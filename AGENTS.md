# Repository Guidelines

## Project Structure & Module Organization

This repository is a Python-based Frank Gemini service. Application code lives in `src/`, with `src/main.py` as the orchestration entry point. Core packages are grouped by responsibility: `analyst/` for LLM and risk auditing, `scraper/` for market data, `strategist/` for technical analysis and trade advice, `listener/` for Feishu WebSocket handling, `notifier/` for Feishu delivery, and `generator/` for Markdown/card output. Tests and verification scripts live in `tests/`. Project documentation is under `doc/`, deployment helpers under `scripts/`, persistent runtime data under `data/`, and logs under `logs/`.

## Build, Test, and Development Commands

- `python -m pip install -r requirements.txt`: install runtime dependencies.
- `python src/main.py`: run the service locally after required environment variables are configured.
- `python tests/run_tests.py`: run the full `unittest` suite discovered from `tests/test_*.py`.
- `python tests/verify_connectivity.py`: verify external API connectivity when credentials are available.
- `docker compose build`: build the application image from `Dockerfile`.
- `docker compose up -d`: start the containerized service with mounted `src/`, `tests/`, `data/`, and `logs/`.
- `bash scripts/build_release.sh`: package a release ZIP for Windows deployment.

## Coding Style & Naming Conventions

Use Python 3 style with 4-space indentation. Keep module names lowercase with underscores, matching existing files such as `risk_auditor.py` and `trade_advisor.py`. Use descriptive class and function names tied to business roles. Prefer small modules grouped by domain responsibility. Comments may be Chinese where they explain business rules or operational constraints; keep routine code self-explanatory.

## Testing Guidelines

Tests use Python `unittest`. Add new tests in `tests/` with filenames matching `test_*.py` so `tests/run_tests.py` discovers them automatically. Prefer mocks for external systems such as AkShare, Feishu, and LLM APIs. For changes touching scheduling, state transitions, alerts, or data fallback behavior, include both success and failure-path tests.

## Commit & Pull Request Guidelines

Git history uses short conventional prefixes such as `feat:` and `init:`. Continue with concise messages like `feat: add risk alert fallback` or `fix: handle missing market data`. Pull requests should include a clear summary, test evidence, linked issue or design document when available, and screenshots or message-card previews for Feishu UI changes.

## Security & Configuration Tips

Do not commit real API keys, database passwords, Feishu secrets, tokens, or local `.env` values. Use placeholders such as `{provided_by_ops}` in examples. Treat files under `data/` and `logs/` as runtime artifacts unless a specific fixture or report is intentionally required.
