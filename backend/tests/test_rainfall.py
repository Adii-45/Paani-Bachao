import gzip
import json
from pathlib import Path

from app.domain.location import NormalizedLocation
from app.provenance.models import DataStatus
from app.providers.rainfall.normalized import NormalizedImdRainfallProvider


def location(latitude: float = 12.5, longitude: float = 77.5) -> NormalizedLocation:
    return NormalizedLocation(
        input="Example",
        canonicalName="Example District, Example State, India",
        latitude=latitude,
        longitude=longitude,
        district="Example District",
        state="Example State",
        country="India",
        provider="test fixture",
        confidence="fixture",
    )


def write_dataset(path: Path, *, status: str = "DATA_AVAILABLE") -> None:
    # Provider-contract fixture only; no fixture value is used by production.
    payload = {
        "dataset_status": status,
        "source_id": "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020",
        "dataset_title": "Test fixture",
        "dataset_version": "fixture-v1",
        "imported_at": "2026-08-13T00:00:00Z",
        "records": [
            {
                "record_id": "fixture-district-1",
                "location_name": "Example District",
                "state": "Example State",
                "district": "Example District",
                "latitude": None,
                "longitude": None,
                "rainfall_mm": 1000,
                "statistic_type": "LONG_PERIOD_NORMAL_ANNUAL",
                "reference_period": "fixture-period",
                "spatial_resolution": "district polygon fixture",
                "source_id": "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020",
                "source_name": "India Meteorological Department (IMD)",
                "source_url": "https://example.invalid/fixture",
                "source_record": "fixture-row-1",
                "dataset_version": "fixture-v1",
                "retrieved_at": "2026-08-13T00:00:00Z",
                "bounding_box": [77.0, 12.0, 78.0, 13.0],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [[77.0, 12.0], [78.0, 12.0], [78.0, 13.0], [77.0, 13.0], [77.0, 12.0]]
                    ],
                },
            }
        ],
    }
    if path.suffix == ".gz":
        with gzip.open(path, "wt", encoding="utf-8") as destination:
            json.dump(payload, destination)
    else:
        path.write_text(json.dumps(payload), encoding="utf-8")


def test_spatial_lookup_preserves_rainfall_provenance(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json.gz"
    write_dataset(dataset)

    result = NormalizedImdRainfallProvider(dataset).lookup(location())

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.record is not None
    assert result.record.rainfall_mm == 1000
    assert result.record.reference_period == "fixture-period"
    assert result.record.spatial_resolution == "district polygon fixture"
    assert result.record.source_id == "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020"
    assert result.record.source_name == "India Meteorological Department (IMD)"


def test_checked_in_imd_cache_resolves_bengaluru_coordinate() -> None:
    """IMD annual district-normal map, feature ID 43 (BANGLORE URBAN)."""

    result = NormalizedImdRainfallProvider().lookup(
        location(latitude=12.9716, longitude=77.5946)
    )

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.record is not None
    assert result.record.district == "BANGLORE URBAN"
    assert result.record.rainfall_mm == 822.1
    assert result.record.reference_period == "1971-2020"


def test_missing_dataset_never_falls_back_to_demo_values(tmp_path: Path) -> None:
    result = NormalizedImdRainfallProvider(tmp_path / "missing.json.gz").lookup(
        location()
    )

    assert result.status is DataStatus.DATA_UNAVAILABLE
    assert result.record is None
    assert result.error_code == "RAINFALL_DATA_UNAVAILABLE"


def test_coordinate_outside_imported_polygons_is_explicit(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset)

    result = NormalizedImdRainfallProvider(dataset).lookup(location(0, 0))

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.record is None
    assert result.error_code == "RAINFALL_DATA_UNAVAILABLE"


def test_stale_cache_is_labelled_not_hidden(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset, status="STALE")

    result = NormalizedImdRainfallProvider(dataset).lookup(location())

    assert result.status is DataStatus.DATA_STALE
    assert result.record is not None
    assert "stale" in result.message.lower()
