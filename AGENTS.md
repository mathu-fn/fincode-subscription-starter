# Repository Guidelines

## Project Structure & Module Organization

This repository is a React + FastAPI starter for fincode subscription flows. Backend code lives in `backend/app/`; the current ASGI entrypoint is `backend/app/main.py`. Backend tests live in `backend/tests/` and should mirror the feature or endpoint under test. Frontend code lives in `frontend/src/`, with `App.tsx`, `main.tsx`, and shared CSS in `styles.css`. Project documentation and API specs live in `docs/`, including `docs/api/openapi.yml` and architecture notes. Generated or local dependency folders such as `backend/.venv/`, `backend/.pytest_cache/`, `frontend/node_modules/`, and `frontend/dist/` are ignored and should not be edited directly.

## Build, Test, and Development Commands

Run backend commands from `backend/`:

```bash
uv sync
uv run uvicorn app.main:app --reload
uv run pytest
```

`uv sync` installs Python dependencies from `pyproject.toml` and `uv.lock`. `uvicorn` starts the FastAPI API at `http://127.0.0.1:8000`. `pytest` runs backend tests.

Run frontend commands from `frontend/`:

```bash
npm install
npm run dev
npm run build
npm run preview
```

`npm run dev` starts Vite, `npm run build` type-checks and builds production assets, and `npm run preview` serves the built app locally.

## Coding Style & Naming Conventions

Use Python type hints and small FastAPI route functions. Name Python tests `test_*.py` and test functions `test_*`. Use 4-space indentation for Python. For React, use TypeScript, function components, PascalCase component names, and camelCase variables. Keep environment-facing values in Vite variables such as `VITE_API_BASE_URL`.

## Testing Guidelines

Backend tests use `pytest` with FastAPI `TestClient`; add tests near changed endpoints or services. Do not call real fincode APIs in automated tests; mock external payment clients. The frontend currently has no `npm test` script, so validate UI changes with `npm run build` unless a test runner is added.

## Commit & Pull Request Guidelines

Follow the documented commit prefixes in `docs/architecture/commit-guidelines.md`: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, and `security`. Keep commits small and independently revertible, separating API contract changes, React UI changes, schema changes, and tests. Pull requests should describe the change, list verification commands, link relevant issues, and include screenshots for visible UI changes.

## Security & Configuration Tips

Never commit `.env`, JWT secrets, fincode API keys, card data, CVC values, tokens, or personal data. Browser code may tokenize cards with fincode.js, but all other fincode operations should stay server-side.
