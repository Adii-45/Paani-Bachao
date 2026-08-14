# Phase 2 environmental data layer

`EnvironmentalDataService` is the single assessment-time orchestration boundary. It
resolves the user's text or supplied coordinates, then passes the resulting
`NormalizedLocation` independently to rainfall, groundwater, soil and hydrogeology
providers. `create_assessment` does not read a cache or implement a spatial matching
rule directly. Runtime assessment requests do not call IMD, CGWB, NWIC or Bhuvan;
the Nominatim resolver is the only default runtime network provider when coordinates
are not supplied.

```text
LocationQuery
  -> LocationResolver
  -> NormalizedLocation (latitude/longitude + administrative metadata)
  -> EnvironmentalDataService
       -> NormalizedImdRainfallProvider
       -> NormalizedCgwbGroundwaterProvider
       -> NormalizedOfficialSoilProvider
       -> NormalizedOfficialHydrogeologyProvider
  -> independent typed lookup results
  -> assessment engine
```

The API preserves detailed rainfall evidence under `derived.rainfall` and AR evidence
under `artificialRecharge.environmentalProfile`. The additive `environmentalData`
block provides a compact status, evidence-presence flag, message and source IDs for
all four providers. Hydrogeology also reports geology, geomorphology, aquifer and
groundwater-prospect statuses independently. Failure in one provider never supplies
a value for another provider.

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

The NWIC/GSI service documents separate polygon layers for Principal Aquifers and
Major Aquifers. Its published schema distinguishes source object IDs, aquifer labels,
aquifer systems and other separately named source characteristics. The importer does
not relabel those values as geology, geomorphology or numeric recharge properties.

`scripts/ingest_hydrogeology.py` normalizes one reviewed WGS 84 polygon layer at a
time. A feature type and explicit source-field mapping are required. Mappings are
semantically constrained: geology/lithology fields cannot be mapped into an aquifer
layer, and aquifer fields cannot be mapped into a geomorphology layer. The current
approved `NWIC_GSI_AQUIFER_SYSTEMS` source supports `AQUIFER` and documented
lithology/geology context only; it is not treated as a geomorphology or groundwater-
prospect dataset.

Separate normalized layer outputs can be combined into one cache. Runtime lookup:

- preserves every intersecting source feature in `features`;
- composes independent non-conflicting geology and aquifer attributes for the legacy
  `information` field;
- reports a component as `INSUFFICIENT_DATA` if multiple intersecting features claim
  the same semantic component;
- leaves missing fields null and never derives a recharge score.

Example reviewed aquifer-layer import:

```bash
cd backend
.venv/bin/python -m scripts.ingest_hydrogeology reviewed-aquifer.geojson \
  --source-id NWIC_GSI_AQUIFER_SYSTEMS \
  --feature-type AQUIFER \
  --dataset-version "reviewed official version" \
  --source-layer "Principal Aquifers (1)" \
  --spatial-resolution "published layer scale/resolution" \
  --record-id-field objectid \
  --aquifer-type-field aquifer \
  --aquifer-characteristic aquifer_system=system \
  --confirm-official-source
```

Service metadata is not a site attribute. The official endpoint did not return a
reviewable feature export during this implementation run, so the committed production
cache still has zero records. Geology, geomorphology, groundwater prospects and
aquifer status remain explicitly unavailable at runtime until reviewed source polygons
are imported. No value is inferred from the user's soil label or groundwater
observation.

## Cache validation

Inspect all configured environmental caches before running assessments:

```bash
cd backend
.venv/bin/python -m scripts.validate_environmental_cache --all
```

The command exits unsuccessfully when any configured dataset is not usable. Use
`--json` for a machine-readable report. A single reviewed candidate cache can be
checked without exposing its path in the report:

```bash
.venv/bin/python -m scripts.validate_environmental_cache groundwater path/to/cache.json
```

Each report distinguishes `AVAILABLE`, `STALE`, `EMPTY`, `MISSING`, `MALFORMED`,
`PARTIAL` and `UNSUPPORTED_METADATA`. It includes valid/invalid record counts,
provider status, source IDs, dataset version, import timestamp, observation period,
latest groundwater observation, determinable coverage, and populated component
counts.

Freshness semantics are centralized in
`app/services/environmental_validation.py`. By default, the checker respects the
reviewed dataset status instead of inventing a universal age limit: long-period
rainfall normals and static regional maps do not need daily refreshes, while dated
groundwater observations expose their latest observation date. A deployment may
provide explicit positive maximum ages through `EnvironmentalFreshnessConfig` after
those limits have been approved.

Validation checks field types, units/ranges, polygon geometry/bounds and registered
source provenance. Runtime repositories apply the same provider-ready spatial checks,
so a malformed mixed cache is rejected as a whole instead of silently using a valid
subset. Validation does not establish that an upstream file is authoritative; the
operator must still verify the official source, version, layer and feature identifier.

## AR-engine boundary

These providers supply environmental evidence to the later recharge engine. The engine still returns `INSUFFICIENT_DATA` when required infiltration, hydrogeology, water-balance or water-quality evidence is missing; it does not convert absent provider data into a score or default.

## Supported and unavailable behaviour

- Location text is geocoded through the replaceable `LocationResolver`; there is no
  production city-to-coordinate dictionary. Explicit coordinates bypass remote
  geocoding and remain labelled as user-provided coordinates.
- Rainfall is looked up by coordinate against the 696 imported IMD district-normal
  polygons. A missing polygon prevents the RTRWH calculation.
- The bundled groundwater cache has one stale nearby observation. Other districts
  remain unsupported; no district or national default is substituted.
- The committed soil and hydrogeology caches are intentionally empty pending reviewed
  official feature exports. Their providers return unavailable rather than using the
  homeowner's soil selection or inferring subsurface attributes.
- Provider/cache failures are isolated and returned as `PROVIDER_UNAVAILABLE`. An
  unresolved location prevents all four environmental lookups.

Import and refresh remain separate operator workflows. Rainfall refresh is documented
in `rainfall-ingestion.md`; groundwater, soil and hydrogeology commands and source-
review requirements are documented in the sections above. Run the cache validator
after every import before using the data in an assessment.
