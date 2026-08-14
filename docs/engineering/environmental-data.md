# Phase 1 environmental data layer

The assessment resolves a user location first, then invokes three independent local-cache providers. Runtime assessment requests do not call CGWB, NWIC, Bhuvan or another external environmental service.

## Groundwater

- Parameter: depth to water level, metres below ground level (`m bgl`).
- Observation source: CGWB, *November ground water level data 1994–2023*, station measurement dated 5 November 2022.
- Station-coordinate source: CGWB, *Ground Water Quality Data 2020*, Karnataka row 2767.
- Cache: `backend/app/data/normalized/cgwb_groundwater_observations.json`.
- Current coverage: one cross-checked Bengaluru Urban station (`W125200077350001`, Jayanagar).
- Ingestion: join a reviewed CGWB/India-WRIS water-level CSV to a reviewed official
  station-coordinate CSV by station ID using
  `scripts/ingest_cgwb_groundwater.py`. The importer rejects missing depth,
  unsupported units, invalid coordinates, duplicate station IDs and conflicting
  district/state metadata. Dataset freshness (`DATA_AVAILABLE` or `DATA_STALE`) is
  an explicit operator-reviewed import argument; the application does not invent an
  age threshold.
- Lookup: select the nearest imported station within the resolved state and district;
  if the same coordinates have multiple observations, prefer the newest observation
  date and then station ID. There is no invented maximum radius and no fallback to
  another district. A deployment may supply an explicitly reviewed maximum distance,
  in which case observations beyond it return `UNSUPPORTED_LOCATION`.
- Quality: `DATA_STALE` and `NEARBY_OBSERVATION`. This is not the property's groundwater level and is not sufficient by itself for recharge design.
- Refresh: obtain the latest official seasonal CGWB/India-WRIS export, join it to official station coordinates by station ID, review source metadata, validate the normalized cache, and replace the versioned cache. Seasonal observations must remain separate.

Example import from reviewed local exports:

```bash
cd backend
.venv/bin/python -m scripts.ingest_cgwb_groundwater \
  --observations path/to/reviewed-water-levels.csv \
  --stations path/to/reviewed-stations.csv \
  --dataset-version "reviewed source version" \
  --dataset-status DATA_STALE \
  --confirm-official-sources
```

The command performs no live network call. Source acquisition and review remain a
separate operator step.

## Soil and infiltration

NWIC publishes the `Soil_1New` ArcGIS service at
`https://gis.nwic.in/server/rest/services/SubInfoSysLCC/Soil_1New/MapServer`.
The service advertises map/query capability and GeoJSON support, but its soil
sublayer schema/features were not reliably retrievable during implementation. The
committed production cache therefore still has zero records and returns
`DATA_UNAVAILABLE`; it does not contain synthetic polygons.

`scripts/ingest_nwic_soil.py` normalizes a separately acquired and reviewed official
WGS 84 GeoJSON polygon export. The operator must explicitly provide the source-field
mapping, dataset version, source layer and published spatial resolution. The importer
rejects malformed polygons, invalid coordinates, duplicate source identifiers and
unregistered provenance. Runtime lookup includes polygon boundaries; if overlapping
polygons both contain a coordinate, the result is `INSUFFICIENT_DATA` rather than an
arbitrary selection.

Example import from a reviewed local export:

```bash
cd backend
.venv/bin/python -m scripts.ingest_nwic_soil reviewed-soil.geojson \
  --dataset-version "reviewed official version" \
  --source-layer "published layer name" \
  --spatial-resolution "published map scale or resolution" \
  --record-id-field "reviewed source ID field" \
  --soil-class-field "reviewed soil class field" \
  --confirm-official-source
```

The command performs no network call. It does not establish that an input file is
official merely because the confirmation flag was supplied; source acquisition,
licensing and attribute mapping require operator review.

A regional soil class is never converted into hydraulic conductivity or an
infiltration rate. `measuredInfiltrationRateMmPerHr` remains null and
`fieldTestRecommended` remains true for every imported regional polygon. A
property-level field infiltration/percolation test is still required before design.
The homeowner's descriptive soil selection is retained for compatibility but is not
engineering evidence.

## Geology, geomorphology and aquifer context

Verified official service families include:

- NWIC/GSI `AquiferSystems_GSI`, with principal and major aquifer polygon layers;
- NWIC `AquiferLitholog_NWIC`;
- NRSC Bhuvan documented OGC thematic services;
- CGWB NAQUIM reports.

Service metadata is not a site attribute. Because no reviewed intersecting feature export could be imported reliably, the committed hydrogeology cache has zero records. Geology, geomorphology, groundwater prospects and aquifer status each return an explicit unavailable status; no value is inferred from the user's soil label or groundwater observation.

## Cache validation

After obtaining and reviewing an official export, validate normalized records before replacing a runtime cache:

```bash
cd backend
.venv/bin/python scripts/validate_environmental_cache.py groundwater app/data/normalized/cgwb_groundwater_observations.json
```

Use `soil` or `hydrogeology` for the corresponding schema. Validation checks field types, units/ranges and source-registry identifiers. It does not establish that an upstream file is authoritative; the operator must verify and record the official source, version, layer and feature identifier.

## AR-engine boundary

These providers supply environmental evidence to the later recharge engine. The engine still returns `INSUFFICIENT_DATA` when required infiltration, hydrogeology, water-balance or water-quality evidence is missing; it does not convert absent provider data into a score or default.
