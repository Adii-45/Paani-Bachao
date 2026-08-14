# Phase 1 environmental data layer

The assessment resolves a user location first, then invokes three independent local-cache providers. Runtime assessment requests do not call CGWB, NWIC, Bhuvan or another external environmental service.

## Groundwater

- Parameter: depth to water level, metres below ground level (`m bgl`).
- Observation source: CGWB, *November ground water level data 1994–2023*, station measurement dated 5 November 2022.
- Station-coordinate source: CGWB, *Ground Water Quality Data 2020*, Karnataka row 2767.
- Cache: `backend/app/data/normalized/cgwb_groundwater_observations.json`.
- Current coverage: one cross-checked Bengaluru Urban station (`W125200077350001`, Jayanagar).
- Lookup: select the nearest imported station within the resolved state and district; return the calculated distance. There is no invented maximum radius and no fallback to another district.
- Quality: `DATA_STALE` and `NEARBY_OBSERVATION`. This is not the property's groundwater level and is not sufficient by itself for recharge design.
- Refresh: obtain the latest official seasonal CGWB/India-WRIS export, join it to official station coordinates by station ID, review source metadata, validate the normalized cache, and replace the versioned cache. Seasonal observations must remain separate.

## Soil and infiltration

NWIC publishes the `Soil_1New` ArcGIS service at `https://gis.nwic.in/server/rest/services/SubInfoSysLCC/Soil_1New/MapServer`. During implementation the service metadata was available, but its sublayer schemas/features were not reliably retrievable. The committed cache therefore has zero records and returns `FIELD_MEASUREMENT_REQUIRED`.

A regional soil class is not converted into hydraulic conductivity or an infiltration rate. A property-level field infiltration/percolation test is still required before design. The homeowner's descriptive soil selection is retained for compatibility but is not engineering evidence.

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
