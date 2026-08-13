# Paani Bachao

Paani Bachao is a focused MVP for preliminary residential rooftop rainwater harvesting (RTRWH) and artificial recharge (AR) assessment. A homeowner enters six simple site details and receives a transparent, deterministic result.

> The repository ships with an explicitly marked **demo ruleset** so the complete flow can be tried locally. Those values are not validated engineering data and must not be used for construction. The production ruleset is intentionally empty.

## Architecture

- `frontend/` — Next.js 16 + TypeScript user interface
- `backend/` — FastAPI API, validation, calculation modules, and rule loading
- `backend/app/data/demo/` — isolated, unvalidated development values
- `backend/app/data/production/` — configurable placeholders for validated data

Calculation code is independent of API and UI code. Rainfall access, runoff coefficients, recharge classification, storage sizing, structure selection, and dimensions are all configuration-driven.

## Run locally

Requirements: Node.js 20+, npm, Python 3.11+.

### Backend

```bash
cd backend
uv venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API is available at `http://localhost:8000`, with interactive documentation at `http://localhost:8000/docs`.

### Frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`. Suggested demo locations are Bengaluru, Chennai, Delhi, Hyderabad, and Mumbai.

## Developer checks

After installing the backend and frontend dependencies, install the pre-commit development tool into the backend virtual environment and activate the Git hook once per clone:

```bash
uv pip install --python backend/.venv/bin/python -r requirements-dev.txt
backend/.venv/bin/pre-commit install
```

The committed `.pre-commit-config.yaml` runs fast file validation, Python syntax checks, and ESLint on staged frontend files before each commit. Run every hook manually with:

```bash
backend/.venv/bin/pre-commit run --all-files
```

Pre-commit is an early local check; GitHub Actions remains the source of full lint, type-check, test, and production-build verification.

## Tests

```bash
cd backend
.venv/bin/python -m pytest

cd ../frontend
npm run lint
npm run typecheck
npm test
npm run build
```

## Continuous integration

CI runs automatically on pushes and pull requests to `main`. Separate frontend and backend jobs check linting, types, tests, application imports, and the production build using the repository's existing npm and Python dependency files.

## Rulesets

Development defaults to the `demo` ruleset. Every API response using it includes `isDemoData: true` and the warning `DEMO / DEVELOPMENT VALUE — NOT VALIDATED`.

To run with the intentionally empty production placeholders:

```bash
RAINASSESS_RULESET=production uvicorn app.main:app --reload --port 8000
```

Add reviewed data to `backend/app/data/production/` without changing calculation code. Do not copy the demo values into production. Unknown or missing values produce an unavailable/incomplete result instead of a fabricated estimate.

## API

`POST /api/assessment`

```json
{
  "location": "Bengaluru",
  "roofAreaM2": 120,
  "roofMaterial": "RCC",
  "soilType": "SANDY_LOAM",
  "groundwaterDepthM": 8,
  "availableGroundAreaM2": 15
}
```

Validation rejects empty locations, non-positive roof areas, negative groundwater/ground areas, and unsupported material or soil enums.

## Scope

This build intentionally has no authentication, profiles, demand modelling, reports, government integration, AI, GIS, payments, sensors, or other post-MVP functionality.
