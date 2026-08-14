import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.domain.environmental_validation import (
    CacheValidationStatus,
    EnvironmentalDataset,
)
from app.provenance.models import DataStatus
from app.services.environmental_validation import EnvironmentalCacheValidator

AS_OF = datetime(2026, 8, 13, tzinfo=UTC)


def polygon() -> dict[str, Any]:
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [77.0, 12.0],
                [78.0, 12.0],
                [78.0, 14.0],
                [77.0, 14.0],
                [77.0, 12.0],
            ]
        ],
    }


def rainfall_record(record_id: str = "rain-1") -> dict[str, Any]:
    return {
        "record_id": record_id,
        "location_name": "Fixture District",
        "state": "Fixture State",
        "district": "Fixture District",
        "rainfall_mm": 1000,
        "statistic_type": "LONG_PERIOD_NORMAL_ANNUAL",
        "reference_period": "1971-2020",
        "spatial_resolution": "district polygon fixture",
        "source_id": "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020",
        "source_name": "India Meteorological Department (IMD)",
        "source_url": "https://www.imdpune.gov.in/climinfo/season/ann/index.html",
        "source_record": f"fixture {record_id}",
        "dataset_version": "1971-2020 fixture",
        "retrieved_at": "2026-08-13T00:00:00Z",
        "bounding_box": [77.0, 12.0, 78.0, 14.0],
        "geometry": polygon(),
    }


def rainfall_payload(*records: dict[str, Any], status: str = "DATA_AVAILABLE") -> dict[str, Any]:
    return {
        "dataset_status": status,
        "dataset_version": "1971-2020 fixture",
        "imported_at": "2026-08-13T00:00:00Z",
        "record_count": len(records),
        "records": list(records),
    }


def groundwater_payload(*, status: str = "DATA_AVAILABLE") -> dict[str, Any]:
    return {
        "datasetStatus": status,
        "datasetVersion": "seasonal fixture",
        "importedAt": "2026-08-13T00:00:00Z",
        "recordCount": 1,
        "records": [
            {
                "stationId": "station-1",
                "stationName": "Fixture station",
                "depthBelowGroundLevelM": 8,
                "depthUnit": "m bgl",
                "observationDate": "2022-11-05",
                "season": "NOVEMBER_MONITORING",
                "latitude": 12.9,
                "longitude": 77.5,
                "district": "Fixture District",
                "state": "Fixture State",
                "spatialResolution": "NEARBY_OBSERVATION",
                "provenance": {
                    "quality": "AUTHORITATIVE_DATASET",
                    "sourceIds": [
                        "CGWB_GWL_NOVEMBER_2022",
                        "CGWB_WQ_2020_STATION_COORDINATES",
                    ],
                    "sourceRecord": "fixture station-1",
                },
            }
        ],
    }


def soil_payload() -> dict[str, Any]:
    return {
        "datasetStatus": "DATA_AVAILABLE",
        "datasetVersion": "soil fixture",
        "importedAt": "2026-08-13T00:00:00Z",
        "recordCount": 1,
        "records": [
            {
                "recordId": "soil-1",
                "soilClass": "Mapped fixture class",
                "datasetVersion": "soil fixture",
                "infiltrationDataType": "REGIONAL_SOIL_PROXY",
                "spatialResolution": "REGIONAL_LAYER",
                "fieldTestRecommended": True,
                "boundingBox": [77.0, 12.0, 78.0, 14.0],
                "geometry": polygon(),
                "provenance": {
                    "quality": "AUTHORITATIVE_DATASET",
                    "sourceIds": ["NWIC_SOIL_SERVICE"],
                    "sourceRecord": "fixture soil-1",
                },
            }
        ],
    }


def hydrogeology_payload() -> dict[str, Any]:
    return {
        "datasetStatus": "DATA_AVAILABLE",
        "datasetVersion": "aquifer fixture",
        "importedAt": "2026-08-13T00:00:00Z",
        "recordCount": 1,
        "records": [
            {
                "recordId": "aquifer-1",
                "featureType": "AQUIFER",
                "sourceFeatureId": "1",
                "aquiferType": "Mapped fixture aquifer",
                "spatialResolution": "REGIONAL_LAYER",
                "datasetVersion": "aquifer fixture",
                "boundingBox": [77.0, 12.0, 78.0, 14.0],
                "geometry": polygon(),
                "provenance": {
                    "quality": "AUTHORITATIVE_DATASET",
                    "sourceIds": ["NWIC_GSI_AQUIFER_SYSTEMS"],
                    "sourceRecord": "fixture aquifer-1",
                },
            }
        ],
    }


def write(path: Path, payload: dict[str, Any]) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def validator(
    dataset: EnvironmentalDataset, path: Path
) -> EnvironmentalCacheValidator:
    return EnvironmentalCacheValidator(paths={dataset: path}, as_of=AS_OF)


def test_valid_cache_reports_coverage_source_and_provider_status(tmp_path: Path) -> None:
    path = write(tmp_path / "rainfall.json", rainfall_payload(rainfall_record()))

    report = validator(EnvironmentalDataset.RAINFALL, path).validate(
        EnvironmentalDataset.RAINFALL
    )

    assert report.status is CacheValidationStatus.AVAILABLE
    assert report.provider_status is DataStatus.DATA_AVAILABLE
    assert report.usable is True
    assert report.record_count == report.valid_record_count == 1
    assert report.coverage is not None
    assert report.coverage.bounding_box == (77.0, 12.0, 78.0, 14.0)
    assert report.observation_period == "1971-2020"
    assert report.source_ids == ["IMD_DISTRICT_ANNUAL_NORMALS_1971_2020"]


def test_empty_cache_is_not_usable(tmp_path: Path) -> None:
    path = write(
        tmp_path / "soil.json",
        {
            "datasetStatus": "DATA_UNAVAILABLE",
            "datasetVersion": None,
            "importedAt": None,
            "records": [],
        },
    )

    report = validator(EnvironmentalDataset.SOIL, path).validate(
        EnvironmentalDataset.SOIL
    )

    assert report.status is CacheValidationStatus.EMPTY
    assert report.provider_status is DataStatus.DATA_UNAVAILABLE
    assert report.usable is False


def test_missing_cache_is_reported_without_exposing_a_path(tmp_path: Path) -> None:
    report = validator(
        EnvironmentalDataset.GROUNDWATER, tmp_path / "private-missing.json"
    ).validate(EnvironmentalDataset.GROUNDWATER)

    assert report.status is CacheValidationStatus.MISSING
    assert report.provider_status is DataStatus.PROVIDER_UNAVAILABLE
    assert "private-missing" not in " ".join(report.issues)


def test_stale_groundwater_preserves_latest_observation(tmp_path: Path) -> None:
    path = write(
        tmp_path / "groundwater.json",
        groundwater_payload(status="DATA_STALE"),
    )

    report = validator(EnvironmentalDataset.GROUNDWATER, path).validate(
        EnvironmentalDataset.GROUNDWATER
    )

    assert report.status is CacheValidationStatus.STALE
    assert report.provider_status is DataStatus.DATA_STALE
    assert report.latest_observation_date is not None
    assert report.latest_observation_date.isoformat() == "2022-11-05"
    assert report.observation_period == "2022-11-05 to 2022-11-05"


def test_rainfall_record_missing_provenance_is_malformed(tmp_path: Path) -> None:
    record = rainfall_record()
    del record["source_id"]
    path = write(tmp_path / "rainfall.json", rainfall_payload(record))

    report = validator(EnvironmentalDataset.RAINFALL, path).validate(
        EnvironmentalDataset.RAINFALL
    )

    assert report.status is CacheValidationStatus.MALFORMED
    assert report.invalid_record_count == 1
    assert any("sourceId" in issue for issue in report.issues)


def test_invalid_record_is_reported(tmp_path: Path) -> None:
    record = rainfall_record()
    record["rainfall_mm"] = -1
    path = write(tmp_path / "rainfall.json", rainfall_payload(record))

    report = validator(EnvironmentalDataset.RAINFALL, path).validate(
        EnvironmentalDataset.RAINFALL
    )

    assert report.status is CacheValidationStatus.MALFORMED
    assert report.valid_record_count == 0
    assert report.invalid_record_count == 1


def test_mixed_valid_and_invalid_records_are_partial_and_provider_unsafe(
    tmp_path: Path,
) -> None:
    invalid = rainfall_record("rain-bad")
    invalid["geometry"] = {"type": "Point", "coordinates": [77.5, 13.0]}
    path = write(
        tmp_path / "rainfall.json",
        rainfall_payload(rainfall_record("rain-good"), invalid),
    )

    report = validator(EnvironmentalDataset.RAINFALL, path).validate(
        EnvironmentalDataset.RAINFALL
    )

    assert report.status is CacheValidationStatus.PARTIAL
    assert report.provider_status is DataStatus.DATA_UNAVAILABLE
    assert report.usable is False
    assert report.valid_record_count == report.invalid_record_count == 1


def test_unsupported_metadata_reports_provider_status(tmp_path: Path) -> None:
    payload = rainfall_payload(rainfall_record(), status="UNKNOWN_STATUS")
    path = write(tmp_path / "rainfall.json", payload)

    report = validator(EnvironmentalDataset.RAINFALL, path).validate(
        EnvironmentalDataset.RAINFALL
    )

    assert report.status is CacheValidationStatus.UNSUPPORTED_METADATA
    assert report.provider_status is DataStatus.DATA_UNAVAILABLE
    assert report.usable is False


def test_all_environmental_provider_fixtures_are_reported_together(
    tmp_path: Path,
) -> None:
    paths = {
        EnvironmentalDataset.RAINFALL: write(
            tmp_path / "rainfall.json", rainfall_payload(rainfall_record())
        ),
        EnvironmentalDataset.GROUNDWATER: write(
            tmp_path / "groundwater.json", groundwater_payload(status="DATA_STALE")
        ),
        EnvironmentalDataset.SOIL: write(tmp_path / "soil.json", soil_payload()),
        EnvironmentalDataset.HYDROGEOLOGY: write(
            tmp_path / "hydrogeology.json", hydrogeology_payload()
        ),
    }

    summary = EnvironmentalCacheValidator(paths=paths, as_of=AS_OF).validate_all()

    assert summary.all_usable is True
    assert {report.dataset: report.status for report in summary.reports} == {
        EnvironmentalDataset.RAINFALL: CacheValidationStatus.AVAILABLE,
        EnvironmentalDataset.GROUNDWATER: CacheValidationStatus.STALE,
        EnvironmentalDataset.SOIL: CacheValidationStatus.AVAILABLE,
        EnvironmentalDataset.HYDROGEOLOGY: CacheValidationStatus.AVAILABLE,
    }
    hydro_report = next(
        report
        for report in summary.reports
        if report.dataset is EnvironmentalDataset.HYDROGEOLOGY
    )
    assert hydro_report.component_counts == {
        "geologyOrLithology": 0,
        "geomorphology": 0,
        "aquifer": 1,
        "groundwaterProspect": 0,
    }
