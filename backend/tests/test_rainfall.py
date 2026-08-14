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


def duplicate_polygon_record(
    path: Path,
    *,
    district: str,
    rainfall_mm: float,
) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    duplicate = dict(payload["records"][0])
    duplicate.update(
        {
            "record_id": f"fixture-{district}",
            "location_name": district,
            "district": district,
            "rainfall_mm": rainfall_mm,
            "source_record": f"fixture-{district}",
        }
    )
    payload["records"].append(duplicate)
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
    assert result.record.monthly_normal is not None
    assert result.record.monthly_normal.values_mm == (
        1.2,
        5.2,
        12.5,
        41.7,
        101.8,
        74.9,
        86.4,
        116.9,
        174.3,
        144.4,
        52.2,
        10.5,
    )
    assert result.record.monthly_normal.source_id == (
        "IMD_DISTRICT_MONTHLY_NORMALS_1971_2020"
    )


def test_checked_in_cache_resolves_multiple_locations_without_city_mapping() -> None:
    provider = NormalizedImdRainfallProvider()
    coordinates = (
        (28.6139, 77.2090, "NEW DELHI"),
        (19.0760, 72.8777, "MUMBAI CITY"),
        (13.0827, 80.2707, "CHENNAI"),
        (22.5726, 88.3639, "KOLKATA"),
    )

    for latitude, longitude, expected_district in coordinates:
        result = provider.lookup(location(latitude=latitude, longitude=longitude))

        assert result.status is DataStatus.DATA_AVAILABLE
        assert result.record is not None
        assert result.record.district == expected_district
        assert result.record.rainfall_mm >= 0
        assert result.record.source_id == "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020"


def test_overlapping_polygons_use_matching_administrative_metadata(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset)
    duplicate_polygon_record(dataset, district="Other District", rainfall_mm=2000)

    result = NormalizedImdRainfallProvider(dataset).lookup(location())

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.record is not None
    assert result.record.district == "Example District"
    assert result.record.rainfall_mm == 1000


def test_overlapping_polygons_without_matching_metadata_remain_ambiguous(
    tmp_path: Path,
) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset)
    duplicate_polygon_record(dataset, district="Other District", rainfall_mm=2000)
    unresolved_admin = location().model_copy(update={"district": None, "state": None})

    result = NormalizedImdRainfallProvider(dataset).lookup(unresolved_admin)

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.record is None
    assert result.error_code == "RAINFALL_LOCATION_AMBIGUOUS"


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
