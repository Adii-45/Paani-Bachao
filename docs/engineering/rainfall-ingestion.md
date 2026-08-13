# Official IMD rainfall ingestion

The application does not call a made-up rainfall API and does not use current daily rainfall as an annual normal. An operator must obtain an appropriate long-period annual-normal dataset from IMD through an official data service/supply channel and retain its licence/delivery documentation.

## Required input columns

```text
record_id
location_name
rainfall_mm
reference_period
spatial_resolution
source_record
```

Optional columns are `state`, `district`, `latitude`, and `longitude`. The script never fills missing metadata by inference.

From the backend directory, normalize a verified delivery with:

```bash
python scripts/ingest_imd_rainfall.py path/to/official.csv app/data/normalized/imd_normal_annual_rainfall.json \
  --dataset-title "<exact IMD dataset title>" \
  --dataset-version "<delivery/version identifier>" \
  --confirm-official-source
```

The confirmation flag records an operator decision; it does not independently authenticate a file. Review the resulting diff, source record identifiers, reference period and spatial resolution before release.

## Lookup behaviour

The provider performs exact normalized location/district/state matching. It does not choose the nearest station or interpolate a grid because those operations require a documented spatial method and uncertainty model. Ambiguous locations return `INSUFFICIENT_DATA`; missing records return `UNSUPPORTED_LOCATION`; a missing dataset returns `DATA_UNAVAILABLE`.
