from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from app.domain.environment import LocationQuery
from app.importers.cgwb_groundwater import CGWBGroundwaterImporter
from app.provenance.models import DataStatus
from app.providers.groundwater import NormalizedCgwbGroundwaterProvider
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment

from .test_assessment import BengaluruResolver


IMPORTED_AT = datetime(2026, 8, 13, tzinfo=UTC)


def station(
    station_id: str = "CGWB-001",
    *,
    latitude: object = 12.95,
    longitude: object = 77.58,
    district: str = "Bangalore Urban",
    state: str = "Karnataka",
) -> dict[str, object]:
    return {
        "stationId": station_id,
        "stationName": f"Station {station_id}",
        "stationType": "Piezometer",
        "aquiferNature": "Unconfined",
        "latitude": latitude,
        "longitude": longitude,
        "district": district,
        "state": state,
    }


def observation(
    station_id: str = "CGWB-001",
    *,
    depth: object = 8.25,
    unit: str = "m bgl",
    observation_date: str = "2025-11-15",
    season: str = "POST_MONSOON",
    district: str = "Bangalore Urban",
    state: str = "Karnataka",
) -> dict[str, object]:
    return {
        "stationId": station_id,
        "depthBelowGroundLevel": depth,
        "depthUnit": unit,
        "observationDate": observation_date,
        "season": season,
        "district": district,
        "state": state,
    }


def imported_cache(
    path: Path,
    observations: list[dict[str, object]],
    stations: list[dict[str, object]],
    *,
    status: DataStatus = DataStatus.DATA_AVAILABLE,
) -> Path:
    importer = CGWBGroundwaterImporter()
    normalized = importer.normalize(
        observations,
        stations,
        imported_at=IMPORTED_AT,
        dataset_status=status,
        dataset_version="reviewed deterministic fixture",
    )
    importer.write(normalized, path)
    return path


def test_valid_observation_import_preserves_station_date_season_and_sources() -> None:
    normalized = CGWBGroundwaterImporter().normalize(
        [observation()],
        [station()],
        imported_at=IMPORTED_AT,
        dataset_status=DataStatus.DATA_AVAILABLE,
        dataset_version="CGWB reviewed fixture",
    )

    assert normalized["recordCount"] == 1
    record = normalized["records"][0]
    assert record["stationId"] == "CGWB-001"
    assert record["stationName"] == "Station CGWB-001"
    assert record["stationType"] == "Piezometer"
    assert record["aquiferNature"] == "Unconfined"
    assert record["depthBelowGroundLevelM"] == 8.25
    assert record["depthUnit"] == "m bgl"
    assert record["observationDate"] == "2025-11-15"
    assert record["season"] == "POST_MONSOON"
    assert record["provenance"]["sourceIds"] == [
        "CGWB_GWL_NOVEMBER_2022",
        "CGWB_WQ_2020_STATION_COORDINATES",
    ]


@pytest.mark.parametrize(
    ("field", "value"),
    (("latitude", 91), ("latitude", -91), ("longitude", 181), ("longitude", -181)),
)
def test_import_rejects_invalid_station_coordinates(field: str, value: float) -> None:
    station_row = station()
    station_row[field] = value

    with pytest.raises(ValueError, match="Invalid coordinates"):
        CGWBGroundwaterImporter().normalize(
            [observation()],
            [station_row],
            imported_at=IMPORTED_AT,
            dataset_status=DataStatus.DATA_AVAILABLE,
            dataset_version="fixture",
        )


def test_import_rejects_missing_groundwater_depth() -> None:
    row = observation()
    del row["depthBelowGroundLevel"]

    with pytest.raises(ValueError, match="depthBelowGroundLevel"):
        CGWBGroundwaterImporter().normalize(
            [row],
            [station()],
            imported_at=IMPORTED_AT,
            dataset_status=DataStatus.DATA_AVAILABLE,
            dataset_version="fixture",
        )


def test_depth_unit_variants_are_normalized_to_metres_below_ground_level() -> None:
    normalized = CGWBGroundwaterImporter().normalize(
        [observation(unit="metres below ground level")],
        [station()],
        imported_at=IMPORTED_AT,
        dataset_status=DataStatus.DATA_AVAILABLE,
        dataset_version="fixture",
    )

    record = normalized["records"][0]
    assert record["depthBelowGroundLevelM"] == 8.25
    assert record["depthUnit"] == "m bgl"


def test_nearest_same_district_observation_is_selected(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [observation("CGWB-001"), observation("CGWB-002", depth=5.5)],
        [
            station("CGWB-001", latitude=12.8, longitude=77.4),
            station("CGWB-002", latitude=12.97, longitude=77.59),
        ],
    )
    location = BengaluruResolver().resolve(LocationQuery(location="Bengaluru")).location
    assert location is not None

    result = NormalizedCgwbGroundwaterProvider(path).lookup(location)

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.observation is not None
    assert result.observation.station_id == "CGWB-002"
    assert result.observation.depth_below_ground_level_m == 5.5


def test_observation_outside_configured_distance_is_unavailable(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [observation()],
        [station(latitude=12.0, longitude=77.0)],
    )
    location = BengaluruResolver().resolve(LocationQuery(location="Bengaluru")).location
    assert location is not None

    result = NormalizedCgwbGroundwaterProvider(
        path, max_distance_m=1_000
    ).lookup(location)

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.observation is None
    assert "configured" in result.message


def test_incompatible_district_never_leaks_an_observation(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [observation(district="Mysore")],
        [station(district="Mysore")],
    )
    location = BengaluruResolver().resolve(LocationQuery(location="Bengaluru")).location
    assert location is not None

    result = NormalizedCgwbGroundwaterProvider(path).lookup(location)

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.observation is None


def test_stale_import_is_preserved_by_provider(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [observation()],
        [station()],
        status=DataStatus.DATA_STALE,
    )
    location = BengaluruResolver().resolve(LocationQuery(location="Bengaluru")).location
    assert location is not None

    result = NormalizedCgwbGroundwaterProvider(path).lookup(location)

    assert result.status is DataStatus.DATA_STALE
    assert result.observation is not None


def test_same_station_multiple_observations_selects_newest_date(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [
            observation(depth=9.0, observation_date="2024-11-15"),
            observation(depth=7.0, observation_date="2025-11-15"),
        ],
        [station()],
    )
    location = BengaluruResolver().resolve(LocationQuery(location="Bengaluru")).location
    assert location is not None

    result = NormalizedCgwbGroundwaterProvider(path).lookup(location)

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.record_count == 2
    assert result.observation is not None
    assert result.observation.observation_date == date(2025, 11, 15)
    assert result.observation.depth_below_ground_level_m == 7.0


def test_imported_groundwater_flows_into_assessment_profile(tmp_path: Path) -> None:
    path = imported_cache(
        tmp_path / "groundwater.json",
        [observation()],
        [station()],
    )
    result = create_assessment(
        AssessmentRequest(
            location="Bengaluru",
            roofAreaM2=20,
            roofMaterial="RCC",
            soilType="DONT_KNOW",
            groundwaterDepthM=8,
            availableGroundAreaM2=15,
        ),
        location_resolver=BengaluruResolver(),
        groundwater_provider=NormalizedCgwbGroundwaterProvider(path),
    )

    profile = result.artificialRecharge.environmentalProfile
    assert profile is not None
    assert profile.groundwater.status is DataStatus.DATA_AVAILABLE
    assert profile.groundwater.observation is not None
    assert profile.groundwater.observation.station_id == "CGWB-001"
    assert profile.groundwater.observation.depth_unit == "m bgl"
