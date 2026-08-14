# Paani Bachao

Paani Bachao is a preliminary residential rooftop rainwater harvesting (RTRWH) and artificial recharge (AR) assessment application. Its engineering engine is evidence-first: it returns an unavailable or insufficient-data result rather than silently substituting an unsupported environmental value or design rule.

> An imported IMD 1971-2020 district rainfall-normal record and an applicable CGWB Table 7.2 roof coefficient must both be available before annual rooftop harvest is calculated. Tank sizing additionally requires all 12 monthly normals and an explicit user-entered monthly demand. Artificial-recharge recommendations remain unavailable until their documented engineering inputs are present.

## Architecture

- `frontend/` — Next.js 16 + TypeScript user interface
- `backend/` — FastAPI API, normalized domain types, provider interfaces, source-backed engineering methods, and tests
- `backend/app/data/sources.json` — machine-readable engineering source registry
- `backend/app/data/normalized/` — versioned official datasets imported into the normalized provider format
- `backend/app/data/source_backed/` — engineering records that include source and selection provenance
- `docs/engineering/` — source audit, proposed model, limitations, and ingestion instructions

Environmental providers are independent of engineering calculations and API/UI code. The core engine receives normalized values with provenance, source version, spatial/temporal resolution, and data-quality metadata.

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

Open `http://localhost:3000`. Text locations are resolved to coordinates through a replaceable geocoder, then matched locally against the committed IMD district-normal polygons. Rainfall lookup does not call a weather service and has no fabricated fallback.

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

## Engineering data and provenance

The source matrix and removed-assumption audit are in [`docs/engineering/source-audit.md`](docs/engineering/source-audit.md). The calculation/data model is documented in [`docs/engineering/proposed-model.md`](docs/engineering/proposed-model.md).

The selected IMD product, committed normalized cache, provenance fields and guarded refresh command are documented in [`docs/engineering/rainfall-ingestion.md`](docs/engineering/rainfall-ingestion.md).

## API

`POST /api/assessment`

```json
{
  "location": "Bengaluru",
  "roofAreaM2": 120,
  "roofMaterial": "RCC",
  "soilType": "SANDY_LOAM",
  "groundwaterDepthM": 8,
  "availableGroundAreaM2": 15,
  "monthlyRainwaterDemandLitres": 500
}
```

Validation rejects empty locations, non-positive roof areas, negative groundwater/ground areas, and unsupported material or soil enums.

`monthlyRainwaterDemandLitres` is optional and is needed only for tank sizing; it is
the user's planned constant monthly rainwater use and has no pre-populated default.
Other optional API fields support coordinate/administrative disambiguation (`latitude`,
`longitude`, `state`, `district`) and groundwater observation metadata
(`groundwaterObservationDate`, `groundwaterObservationSeason`,
`groundwaterObservationMethod`, `groundwaterSource`). The application never inserts
values into these fields or presents an application-supplied value as user input.

## Scope

This build intentionally has no authentication, profiles, inferred household-demand
model, reports, government integration, AI, payments, sensors, or other post-assessment
functionality. Tank sizing uses only the explicit monthly planned-use value when the
user supplies it. Provider boundaries exist for future official GIS data, but no
undocumented or scraped Bhuvan service is called.
