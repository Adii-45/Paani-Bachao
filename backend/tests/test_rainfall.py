import json
from pathlib import Path

from app.domain.environment import LocationQuery
from app.provenance.models import DataStatus
from app.providers.rainfall.normalized import (
    NormalizedImdRainfallProvider,
    normalize_location,
)


def write_dataset(path: Path, *, status: str = "DATA_AVAILABLE") -> None:
    # This is a provider-contract fixture, not production rainfall data.
    path.write_text(
        json.dumps(
            {
                "dataset_status": status,
                "source_id": "IMD_NORMAL_RAINFALL_DATASET",
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
                        "spatial_resolution": "district fixture",
                        "source_id": "IMD_NORMAL_RAINFALL_DATASET",
                        "source_record": "fixture-row-1",
                        "dataset_version": "fixture-v1",
                        "retrieved_at": "2026-08-13T00:00:00Z"
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_location_normalization_is_case_and_punctuation_tolerant() -> None:
    assert normalize_location("  Example,   DISTRICT ") == "example district"


def test_exact_official_record_lookup_preserves_metadata(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset)

    result = NormalizedImdRainfallProvider(dataset).lookup(
        LocationQuery(location="example district", state="Example State")
    )

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.record is not None
    assert result.record.rainfall_mm == 1000
    assert result.record.reference_period == "fixture-period"
    assert result.record.spatial_resolution == "district fixture"
    assert result.record.source_id == "IMD_NORMAL_RAINFALL_DATASET"


def test_missing_dataset_never_falls_back_to_demo_values(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset, status="NOT_INGESTED")

    result = NormalizedImdRainfallProvider(dataset).lookup(
        LocationQuery(location="Bengaluru")
    )

    assert result.status is DataStatus.DATA_UNAVAILABLE
    assert result.record is None
    assert "not been ingested" in result.message


def test_unsupported_location_is_explicit(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset)

    result = NormalizedImdRainfallProvider(dataset).lookup(
        LocationQuery(location="Not In Fixture")
    )

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.record is None


def test_stale_cache_is_labelled_not_hidden(tmp_path: Path) -> None:
    dataset = tmp_path / "rainfall.json"
    write_dataset(dataset, status="STALE")

    result = NormalizedImdRainfallProvider(dataset).lookup(
        LocationQuery(location="Example District")
    )

    assert result.status is DataStatus.DATA_STALE
    assert result.record is not None
    assert "stale" in result.message.lower()
