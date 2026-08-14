# Paani Bachao

Paani Bachao is a web application for preliminary Roof Top Rain Water Harvesting
(RTRWH) and Artificial Recharge (AR) assessment. It combines real location
resolution, source-backed environmental evidence, deterministic engineering
calculations, and a homeowner-friendly result page.

The current MVP supports rainfall-based RTRWH assessment across the installed IMD
dataset. Complete AR recommendations are intentionally limited to reviewed regional
coverage; the application reports missing evidence instead of inventing a result.

## Live Demo

- **Frontend (Vercel):** `COMING_SOON_VERCEL_URL`
- **Backend API (Render):** `COMING_SOON_RENDER_URL`

Replace these placeholders after deployment.

## What It Does

```text
Location
  → rainfall and environmental lookup
  → annual RTRWH potential
  → monthly demand-based tank sizing
  → recharge-available tank overflow
  → AR feasibility
  → regional structure selection
  → structure-specific indicative sizing
  → homeowner-friendly result
```

The normal result view emphasizes the final recommendation. Environmental evidence,
calculation details, engineering statuses, and source provenance remain available in
expandable sections for technical review.

## Current Supported AR Coverage

Full end-to-end AR assessment is currently validated for:

- **Hauz Khas, Delhi**
- **Jayanagar, Bengaluru**

Other locations may still receive location resolution, IMD rainfall data, and RTRWH
calculations. Detailed AR assessment additionally requires reviewed groundwater,
soil/infiltration, hydrogeological evidence, and an applicable regional structure
methodology. An unavailable AR result outside the reviewed areas is an intentional
safety outcome, not a fabricated fallback.

See [AR regional coverage](docs/ar-regional-coverage.md) for the exact evidence,
methodologies, and field-verification requirements.

## Key Features

- Real Indian location resolution through OpenStreetMap Nominatim
- IMD 1971–2020 annual and monthly district rainfall normals
- Source-backed annual rooftop harvest calculation
- Monthly rainfall and user-demand-based tank sizing
- Finite-tank monthly storage, supply, and overflow simulation
- Recharge-available overflow calculation without arbitrary recharge fractions
- Source-backed, condition-based AR feasibility
- Regionally constrained AR structure selection
- Structure-specific indicative sizing using applicable CGWB/KSCST guidance
- Conservative handling of stale or missing environmental evidence
- Explicit infiltration, groundwater, water-quality, and field-verification warnings
- Compact homeowner result page with expandable technical evidence and sources
- Automated backend and frontend tests, CI, and pre-commit checks

## Tech Stack

| Area | Technologies |
| --- | --- |
| Frontend | Next.js 16, React 19, TypeScript |
| Backend | FastAPI, Python, Pydantic |
| Data and engineering | IMD rainfall normals; CGWB environmental and hydrogeological evidence; CGWB/KSCST regional structure methodologies; IRICEN storage method |
| Testing and quality | Pytest, Vitest, Testing Library, ESLint, TypeScript type checking, pre-commit, environmental cache validation |
| Deployment | Vercel (frontend), Render (backend API) |

## Project Structure

```text
Paani-Bachao/
├── frontend/                       # Next.js application
├── backend/
│   ├── app/                        # API, providers, domain and engineering logic
│   ├── scripts/                    # Dataset ingestion and cache validation
│   └── tests/                      # Backend unit, API and integration tests
├── docs/
│   ├── ar-regional-coverage.md
│   └── engineering/                # Methods, data sources and limitations
├── .github/workflows/ci.yml
└── .pre-commit-config.yaml
```

Environmental provider code is separated from engineering calculations. Runtime
lookups consume normalized records with source, time, spatial resolution, and
data-quality metadata.

## Local Development

Requirements: Node.js 20+, npm, and Python 3.11+.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

The API runs at `http://localhost:8000`; interactive FastAPI documentation is at
`http://localhost:8000/docs`.

### Frontend

In another terminal:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open `http://localhost:3000`.

### Pre-commit hook

From the repository root, after creating the backend environment:

```bash
backend/.venv/bin/python -m pip install -r requirements-dev.txt
backend/.venv/bin/pre-commit install
```

Run every hook manually with:

```bash
backend/.venv/bin/pre-commit run --all-files
```

## Environment Variables

The frontend reads one public environment variable:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

It is documented in [`frontend/.env.example`](frontend/.env.example). In Vercel,
set `NEXT_PUBLIC_API_URL` to the deployed Render backend URL. Do not place secrets in
this variable because `NEXT_PUBLIC_*` values are exposed to the browser.

No backend environment variable is currently required for local assessment.

## Deployment

### Backend — Render

1. Create a Render web service for this repository and configure `backend` as its
   working/root directory.
2. Install dependencies from `requirements.txt`.
3. Start the FastAPI application with `uvicorn app.main:app`, binding it to Render's
   assigned host and port according to Render's service configuration.
4. Deploy, verify the API and `/docs`, and copy the final Render URL.
5. Set that URL as `NEXT_PUBLIC_API_URL` in the Vercel project.

No Render-specific configuration file is currently committed, so confirm the final
service commands in Render before deployment.

### Frontend — Vercel

1. Import the repository into Vercel.
2. Select `frontend` as the project root directory.
3. Set `NEXT_PUBLIC_API_URL` to the HTTPS Render backend URL.
4. Deploy and replace `COMING_SOON_VERCEL_URL` above with the final URL.

After the backend deploys, replace `COMING_SOON_RENDER_URL` as well.

## Testing

Run the backend suite and environmental cache validation:

```bash
cd backend
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_environmental_cache.py --all
```

Run the complete frontend verification:

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
```

Run repository-wide pre-commit checks from the repository root:

```bash
backend/.venv/bin/pre-commit run --all-files
```

GitHub Actions repeats the supported frontend and backend checks for pushes and pull
requests to `main`.

## Data Sources and Methodology

- **Rainfall:** IMD All India Districtwise Rainfall Normals, 1971–2020, imported into
  a normalized local coordinate-searchable cache.
- **Annual RTRWH volume and runoff coefficients:** CGWB guidance.
- **Storage sizing:** IRICEN monthly cumulative-surplus method using monthly rainfall
  normals and explicit planned monthly demand.
- **Groundwater and hydrogeology:** reviewed CGWB observations and regional evidence.
- **AR selection and sizing:** applicable, spatially restricted CGWB Delhi and
  CGWB/KSCST Bengaluru methodologies.

Detailed engineering documentation:

- [Calculation and data model](docs/engineering/proposed-model.md)
- [Rainfall ingestion](docs/engineering/rainfall-ingestion.md)
- [Environmental data](docs/engineering/environmental-data.md)
- [Artificial recharge methods](docs/engineering/artificial-recharge-phase1.md)
- [Source audit](docs/engineering/source-audit.md)

## Current Limitations

- Complete AR support is limited to the two reviewed regional vertical slices above.
- Groundwater evidence may be a nearby, stale observation and requires current field
  confirmation.
- Regional soil evidence is not a property infiltration measurement; an on-site
  infiltration/percolation test may be required.
- Recharge water quality may require testing before construction.
- Final recharge-well termination and aquifer intake depth require field investigation.
- All structure sizing is preliminary and indicative; it is not construction approval.
