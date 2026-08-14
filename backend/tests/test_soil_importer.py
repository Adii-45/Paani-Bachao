import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.importers.nwic_soil import (
    NWICSoilFieldMapping,
    NWICSoilPolygonImporter,
)
from app.provenance.models import DataStatus
from app.providers.soil import NormalizedOfficialSoilProvider
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment

from .test_assessment import BengaluruResolver
from .test_environmental_providers import bengaluru_location

IMPORTED_AT = datetime(2026, 8, 13, tzinfo=UTC)
FIELDS = NWICSoilFieldMapping(
    record_id="POLYGON_ID",
    soil_class="SOIL_CLASS",
    soil_texture="TEXTURE",
    permeability_class="PERMEABILITY",
    source_category="CATEGORY",
    source_code="SOIL_CODE",
)


def polygon(
    record_id: str = "soil-001",
    *,
    minimum_longitude: float = 77.0,
    minimum_latitude: float = 12.0,
    maximum_longitude: float = 78.0,
    maximum_latitude: float = 14.0,
    properties: dict[str, Any] | None = None,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "POLYGON_ID": record_id,
        "SOIL_CLASS": "Mapped soil group",
        "TEXTURE": "Mapped texture",
        "PERMEABILITY": None,
        "CATEGORY": "Source category",
        "SOIL_CODE": "SC-1",
    }
    if properties is not None:
        attributes.update(properties)
    return {
        "type": "Feature",
        "properties": attributes,
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [
                    [minimum_longitude, minimum_latitude],
                    [maximum_longitude, minimum_latitude],
                    [maximum_longitude, maximum_latitude],
                    [minimum_longitude, maximum_latitude],
                    [minimum_longitude, minimum_latitude],
                ]
            ],
        },
    }


def geojson(*features: dict[str, Any]) -> str:
    return json.dumps({"type": "FeatureCollection", "features": list(features)})


def normalized_cache(path: Path, *features: dict[str, Any]) -> Path:
    normalized = NWICSoilPolygonImporter().normalize(
        geojson(*features),
        imported_at=IMPORTED_AT,
        dataset_version="reviewed deterministic fixture",
        source_layer="reviewed soil polygon layer",
        spatial_resolution="regional polygon fixture",
        fields=FIELDS,
    )
    NWICSoilPolygonImporter.write(normalized, path)
    return path


def test_valid_polygon_ingestion_preserves_only_published_attributes() -> None:
    normalized = NWICSoilPolygonImporter().normalize(
        geojson(polygon()),
        imported_at=IMPORTED_AT,
        dataset_version="reviewed deterministic fixture",
        source_layer="reviewed soil polygon layer",
        spatial_resolution="regional polygon fixture",
        fields=FIELDS,
    )

    assert normalized["recordCount"] == 1
    record = normalized["records"][0]
    assert record["recordId"] == "nwic-soil-soil-001"
    assert record["soilClass"] == "Mapped soil group"
    assert record["soilTexture"] == "Mapped texture"
    assert record["permeabilityClass"] is None
    assert record["sourceCategory"] == "Source category"
    assert record["sourceCode"] == "SC-1"
    assert record["measuredInfiltrationRateMmPerHr"] is None
    assert record["infiltrationDataType"] == "REGIONAL_SOIL_PROXY"
    assert record["fieldTestRecommended"] is True


def test_malformed_polygon_is_rejected() -> None:
    feature = polygon()
    feature["geometry"]["coordinates"][0].pop()  # type: ignore[index]

    with pytest.raises(ValueError, match="ring must be closed"):
        NWICSoilPolygonImporter().normalize(
            geojson(feature),
            imported_at=IMPORTED_AT,
            dataset_version="fixture",
            source_layer="fixture layer",
            spatial_resolution="fixture resolution",
            fields=FIELDS,
        )


def test_coordinate_inside_polygon_returns_regional_soil(tmp_path: Path) -> None:
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", polygon())
    )

    result = provider.lookup(bengaluru_location())

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.information is not None
    assert result.information.soil_class == "Mapped soil group"
    assert result.information.measured_infiltration_rate_mm_per_hr is None
    assert result.information.field_test_recommended is True


def test_coordinate_outside_all_polygons_is_unavailable(tmp_path: Path) -> None:
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", polygon())
    )
    location = bengaluru_location().model_copy(
        update={"latitude": 20.0, "longitude": 80.0}
    )

    result = provider.lookup(location)

    assert result.status is DataStatus.DATA_UNAVAILABLE
    assert result.information is None


def test_coordinate_on_polygon_boundary_is_included_deterministically(
    tmp_path: Path,
) -> None:
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", polygon())
    )
    location = bengaluru_location().model_copy(
        update={"latitude": 13.0, "longitude": 77.0}
    )

    result = provider.lookup(location)

    assert result.status is DataStatus.DATA_AVAILABLE
    assert result.information is not None
    assert result.information.record_id == "nwic-soil-soil-001"


def test_overlapping_polygons_return_explicit_ambiguity_independent_of_order(
    tmp_path: Path,
) -> None:
    first = polygon("soil-a")
    second = polygon(
        "soil-b",
        minimum_longitude=77.5,
        minimum_latitude=12.5,
        maximum_longitude=78.5,
        maximum_latitude=14.5,
    )
    location = bengaluru_location().model_copy(
        update={"latitude": 13.0, "longitude": 77.75}
    )
    statuses = []
    for index, features in enumerate(((first, second), (second, first))):
        provider = NormalizedOfficialSoilProvider(
            normalized_cache(tmp_path / f"soil-{index}.json", *features)
        )
        statuses.append(provider.lookup(location).status)

    assert statuses == [DataStatus.INSUFFICIENT_DATA, DataStatus.INSUFFICIENT_DATA]


def test_missing_soil_classification_remains_null_and_insufficient(
    tmp_path: Path,
) -> None:
    feature = polygon(
        properties={
            "SOIL_CLASS": None,
            "TEXTURE": None,
            "PERMEABILITY": None,
            "CATEGORY": None,
            "SOIL_CODE": None,
        }
    )
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", feature)
    )

    result = provider.lookup(bengaluru_location())

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.information is not None
    assert result.information.soil_class is None
    assert result.information.soil_texture is None
    assert result.information.measured_infiltration_rate_mm_per_hr is None
    assert "No value was inferred" in result.message


def test_source_metadata_and_provenance_survive_ingestion_and_lookup(
    tmp_path: Path,
) -> None:
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", polygon())
    )

    result = provider.lookup(bengaluru_location())

    assert result.information is not None
    assert result.information.dataset_name == "India-WRIS Soil_1New ArcGIS service"
    assert result.information.dataset_version == "reviewed deterministic fixture"
    assert result.information.source_organization == (
        "National Water Informatics Centre (NWIC)"
    )
    assert result.information.provenance.source_ids == ["NWIC_SOIL_SERVICE"]
    assert result.information.provenance.spatial_resolution == (
        "regional polygon fixture"
    )
    assert result.information.provenance.retrieved_at == IMPORTED_AT


def test_imported_soil_flows_into_assessment_environmental_response(
    tmp_path: Path,
) -> None:
    provider = NormalizedOfficialSoilProvider(
        normalized_cache(tmp_path / "soil.json", polygon())
    )

    assessment = create_assessment(
        AssessmentRequest(
            location="Bengaluru",
            roofAreaM2=20,
            roofMaterial="RCC",
            soilType="DONT_KNOW",
            groundwaterDepthM=8,
            availableGroundAreaM2=15,
        ),
        location_resolver=BengaluruResolver(),
        soil_provider=provider,
    )

    profile = assessment.artificialRecharge.environmentalProfile
    assert profile is not None
    assert profile.soil.status is DataStatus.DATA_AVAILABLE
    assert profile.soil.information is not None
    assert profile.soil.information.soil_class == "Mapped soil group"
    assert profile.soil.information.measured_infiltration_rate_mm_per_hr is None
    assert profile.soil.information.field_test_recommended is True
