from datetime import date
import json
from pathlib import Path

from app.domain.location import NormalizedLocation
from app.provenance.models import DataStatus
from app.providers.groundwater import NormalizedCgwbGroundwaterProvider
from app.providers.hydrogeology import NormalizedOfficialHydrogeologyProvider
from app.providers.soil import NormalizedOfficialSoilProvider
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment
from scripts.validate_environmental_cache import validate_cache

from .test_assessment import BengaluruResolver


def bengaluru_location() -> NormalizedLocation:
    return NormalizedLocation(
        input="Bengaluru",
        canonicalName="Bengaluru, Karnataka, India",
        latitude=12.9716,
        longitude=77.5946,
        district="Bengaluru Urban",
        state="Karnataka",
        country="India",
        provider="test fixture",
        confidence="fixture",
    )


def test_coordinate_resolves_nearest_real_cgwb_observation() -> None:
    result = NormalizedCgwbGroundwaterProvider().lookup(bengaluru_location())

    assert result.status is DataStatus.DATA_STALE
    assert result.record_count == 1
    assert result.observation is not None
    assert result.observation.station_id == "W125200077350001"
    assert result.observation.station_name == "Jayanagar"
    assert result.observation.depth_below_ground_level_m == 3.0
    assert result.observation.observation_date == date(2022, 11, 5)
    assert result.observation.season == "NOVEMBER_MONITORING"
    assert result.observation.distance_from_property_m is not None
    assert result.observation.distance_from_property_m > 0
    assert result.observation.provenance.source_ids == [
        "CGWB_GWL_NOVEMBER_2022",
        "CGWB_WQ_2020_STATION_COORDINATES",
    ]
    assert result.observation.provenance.spatial_resolution is not None


def test_groundwater_lookup_does_not_use_distant_default() -> None:
    location = bengaluru_location().model_copy(
        update={"district": "Mysuru", "latitude": 12.2958, "longitude": 76.6394}
    )

    result = NormalizedCgwbGroundwaterProvider().lookup(location)

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.observation is None
    assert "No regional default" in result.message


def test_missing_groundwater_cache_is_explicit(tmp_path: Path) -> None:
    result = NormalizedCgwbGroundwaterProvider(
        tmp_path / "missing.json"
    ).lookup(bengaluru_location())

    assert result.status is DataStatus.PROVIDER_UNAVAILABLE
    assert result.observation is None


def test_committed_groundwater_cache_passes_schema_and_source_validation() -> None:
    path = (
        Path(__file__).resolve().parents[1]
        / "app"
        / "data"
        / "normalized"
        / "cgwb_groundwater_observations.json"
    )

    assert validate_cache(path, "groundwater") == 1


def test_soil_cache_does_not_fabricate_infiltration_rate() -> None:
    result = NormalizedOfficialSoilProvider().lookup(bengaluru_location())

    assert result.status is DataStatus.FIELD_MEASUREMENT_REQUIRED
    assert result.information is None
    assert "field infiltration/percolation test" in result.message


def test_coordinate_resolves_regional_soil_without_fabricating_measurement(
    tmp_path: Path,
) -> None:
    path = tmp_path / "soil.json"
    path.write_text(
        json.dumps(
            {
                "datasetStatus": "DATA_AVAILABLE",
                "records": [
                    {
                        "recordId": "deterministic-soil-fixture",
                        "soilClass": "fixture regional class",
                        "soilTexture": "fixture texture",
                        "permeabilityClass": None,
                        "measuredInfiltrationRateMmPerHr": None,
                        "infiltrationDataType": "REGIONAL_SOIL_PROXY",
                        "spatialResolution": "REGIONAL_LAYER",
                        "fieldTestRecommended": True,
                        "boundingBox": [77.0, 12.0, 78.0, 14.0],
                        "geometry": {
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
                        },
                        "provenance": {
                            "quality": "AUTHORITATIVE_DATASET",
                            "sourceIds": ["NWIC_SOIL_SERVICE"],
                            "sourceRecord": "deterministic test fixture only",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = NormalizedOfficialSoilProvider(path).lookup(bengaluru_location())

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.information is not None
    assert result.information.measured_infiltration_rate_mm_per_hr is None
    assert result.information.field_test_recommended is True
    assert result.information.provenance.source_ids == ["NWIC_SOIL_SERVICE"]


def test_hydrogeology_layers_fail_independently_and_explicitly() -> None:
    result = NormalizedOfficialHydrogeologyProvider().lookup(bengaluru_location())

    assert result.status is DataStatus.DATA_UNAVAILABLE
    assert result.information is None
    assert result.geology_status is DataStatus.DATA_UNAVAILABLE
    assert result.geomorphology_status is DataStatus.DATA_UNAVAILABLE
    assert result.aquifer_status is DataStatus.DATA_UNAVAILABLE
    assert result.groundwater_prospect_status is DataStatus.DATA_UNAVAILABLE


def test_coordinate_resolves_only_hydrogeology_fields_present_in_source(
    tmp_path: Path,
) -> None:
    path = tmp_path / "hydrogeology.json"
    path.write_text(
        json.dumps(
            {
                "datasetStatus": "DATA_AVAILABLE",
                "records": [
                    {
                        "recordId": "deterministic-hydrogeology-fixture",
                        "geology": "fixture geology",
                        "lithology": None,
                        "geomorphology": None,
                        "groundwaterProspect": None,
                        "aquiferType": "fixture aquifer",
                        "aquiferDepth": None,
                        "aquiferThickness": None,
                        "spatialResolution": "REGIONAL_LAYER",
                        "datasetVersion": "test fixture",
                        "boundingBox": [77.0, 12.0, 78.0, 14.0],
                        "geometry": {
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
                        },
                        "provenance": {
                            "quality": "AUTHORITATIVE_DATASET",
                            "sourceIds": ["NWIC_GSI_AQUIFER_SYSTEMS"],
                            "sourceRecord": "deterministic test fixture only",
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    result = NormalizedOfficialHydrogeologyProvider(path).lookup(
        bengaluru_location()
    )

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.information is not None
    assert result.geology_status is DataStatus.DATA_AVAILABLE
    assert result.aquifer_status is DataStatus.DATA_AVAILABLE
    assert result.geomorphology_status is DataStatus.DATA_UNAVAILABLE
    assert result.groundwater_prospect_status is DataStatus.DATA_UNAVAILABLE


def test_coordinates_to_ar_environmental_profile_integration() -> None:
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
    )

    profile = result.artificialRecharge.environmentalProfile
    assert profile is not None
    assert profile.location.latitude == 12.9716
    assert profile.groundwater.status is DataStatus.DATA_STALE
    assert profile.groundwater.observation is not None
    assert profile.groundwater.observation.station_id == "W125200077350001"
    assert profile.soil.status is DataStatus.FIELD_MEASUREMENT_REQUIRED
    assert profile.soil.information is None
    assert profile.hydrogeology.geology_status is DataStatus.DATA_UNAVAILABLE

    criteria = {
        criterion.criterion: criterion
        for criterion in result.artificialRecharge.criteria
    }
    assert criteria["groundwater_observation"].result == "PASSED"
    assert criteria["groundwater_observation"].observedValue == 3.0
    assert criteria["infiltration_or_permeability"].result == "REQUIRES_VERIFICATION"
    assert criteria["hydrogeology_and_aquifer"].result == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.feasibilityStatus == "INSUFFICIENT_DATA"
    assert result.artificialRecharge.recommendedStructure is None
    assert "CGWB_GWL_NOVEMBER_2022" in result.artificialRecharge.sourceIds
    assert "CGWB_WQ_2020_STATION_COORDINATES" in result.artificialRecharge.sourceIds


def test_unresolved_location_skips_all_environmental_providers() -> None:
    from .test_assessment import UnresolvedResolver, request

    result = create_assessment(request(), location_resolver=UnresolvedResolver())

    assert result.artificialRecharge.environmentalProfile is None
    groundwater = next(
        criterion
        for criterion in result.artificialRecharge.criteria
        if criterion.criterion == "groundwater_observation"
    )
    assert groundwater.result == "INSUFFICIENT_DATA"
