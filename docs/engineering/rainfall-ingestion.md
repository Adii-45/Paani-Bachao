# Official IMD rainfall import

## Selected product

The operational inputs are IMD's **All India Districtwise Rainfall Normals
(1971-2020)** annual and January-to-December products:

- product page: https://www.imdpune.gov.in/climinfo/season/ann/index.html
- published feature layer: `layers/Rainfallinmm_1.js`
- monthly product pages: `https://www.imdpune.gov.in/climinfo/normals/{month}/index.html`
- monthly feature layers: `https://www.imdpune.gov.in/climinfo/normals/{month}/layers/Rainfallinmm_1.js`
- methodology/release notice: https://internal.imd.gov.in/press_release/20220414_pr_1572.pdf

IMD's 14 April 2022 notice describes the product as a 50-year rainfall normal based
on 1971-2020 data, replacing the 1961-2010 normal from the 2022 southwest monsoon
season. A long-period annual normal is used for average annual rooftop harvesting
potential. The 12 monthly normals provide the temporal distribution required by the
selected IRICEN normal-year storage method. They are not current weather, a design
storm, or a year-by-year rainfall series and do not establish probabilistic reliability.

## Import architecture

```text
official IMD annual + 12 monthly district GeoJSON layers
        -> IMDDistrictRainfallImporter
        -> compressed normalized local cache
        -> NormalizedRainfallRepository
        -> coordinate-in-district RainfallProvider lookup
```

The committed cache is
`backend/app/data/normalized/imd_normal_annual_rainfall.json.gz`. It contains 696
records as published by the accessed layers, including each district polygon, annual
and monthly normals, source feature identifiers, reference period, source URLs,
import timestamp, and SHA-256 digests of the downloaded source texts. The importer
requires every monthly layer and verifies matching feature IDs and administrative
records before attaching a monthly series. Rainfall lookup does not make a network
request during an assessment.

## Reproducible refresh

From `backend/`, fetch the currently published official layer and rebuild the cache:

```bash
.venv/bin/python -m scripts.ingest_imd_rainfall --confirm-official-source
```

To review or archive the delivery before import:

```bash
.venv/bin/python -m scripts.ingest_imd_rainfall \
  --source-file path/to/Rainfallinmm_1.js \
  --monthly-source-directory path/to/monthly-files \
  --confirm-official-source
```

The monthly directory must contain `jan.js` through `dec.js`.

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
- overlapping source polygons: use matching resolver-supplied district/state metadata
  only when it identifies exactly one published polygon; otherwise
  `INSUFFICIENT_DATA` / `RAINFALL_LOCATION_AMBIGUOUS`
- stale cache marked by an operator: `DATA_STALE`, with provenance retained

There is no fallback to current weather or the removed five-city values.
