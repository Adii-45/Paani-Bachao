# Official IMD rainfall import

## Selected product

The operational annual-potential input is IMD's **All India Districtwise Rainfall
Normals (1971-2020) — Annual** product:

- product page: https://www.imdpune.gov.in/climinfo/season/ann/index.html
- published feature layer: `layers/Rainfallinmm_1.js`
- methodology/release notice: https://internal.imd.gov.in/press_release/20220414_pr_1572.pdf

IMD's 14 April 2022 notice describes the product as a 50-year rainfall normal based
on 1971-2020 data, replacing the 1961-2010 normal from the 2022 southwest monsoon
season. A long-period annual normal is appropriate for estimating annual rooftop
harvesting potential. It is not current weather, a design storm, an event-rainfall
series, or by itself a storage-tank sizing input.

## Import architecture

```text
official IMD district GeoJSON layer
        -> IMDDistrictRainfallImporter
        -> compressed normalized local cache
        -> NormalizedRainfallRepository
        -> coordinate-in-district RainfallProvider lookup
```

The committed cache is
`backend/app/data/normalized/imd_normal_annual_rainfall.json.gz`. It contains 696
records as published by the accessed layer, including each district polygon, annual
normal, source feature identifier, reference period, source URL, import timestamp,
and SHA-256 digest of the downloaded source text. Rainfall lookup does not make a
network request during an assessment.

## Reproducible refresh

From `backend/`, fetch the currently published official layer and rebuild the cache:

```bash
.venv/bin/python -m scripts.ingest_imd_rainfall --confirm-official-source
```

To review or archive the delivery before import:

```bash
.venv/bin/python -m scripts.ingest_imd_rainfall \
  --source-file path/to/Rainfallinmm_1.js \
  --confirm-official-source
```

The confirmation flag requires an operator to acknowledge the source. The importer
validates the wrapped GeoJSON and required IMD fields; it does not infer missing
rainfall values or administrative records.

## Lookup and failure behaviour

The location resolver supplies latitude/longitude. The repository tests that point
against the official cached district polygons, avoiding dependence on literal or
historical district spelling. No nearest-station estimate or spatial interpolation is
performed.

- missing/unreadable cache: `DATA_UNAVAILABLE` / `RAINFALL_DATA_UNAVAILABLE`
- coordinate outside the imported polygons: `UNSUPPORTED_LOCATION`
- overlapping source polygons: `INSUFFICIENT_DATA`
- stale cache marked by an operator: `DATA_STALE`, with provenance retained

There is no fallback to current weather or the removed five-city values.
