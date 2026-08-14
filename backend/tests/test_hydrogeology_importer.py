import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from app.domain.ar_environment import HydrogeologyFeatureType
from app.importers.hydrogeology import (
    HydrogeologyFieldMapping,
    OfficialHydrogeologyPolygonImporter,
)
from app.provenance.models import DataStatus
from app.providers.hydrogeology import NormalizedOfficialHydrogeologyProvider
from app.schemas import AssessmentRequest
from app.services.assessment import create_assessment

from .test_assessment import BengaluruResolver
from .test_environmental_providers import bengaluru_location

IMPORTED_AT = datetime(2026, 8, 13, tzinfo=UTC)
SOURCE_ID = "NWIC_GSI_AQUIFER_SYSTEMS"


def feature(
    feature_id: str = "1",
    *,
    properties: dict[str, Any] | None = None,
    minimum_longitude: float = 77.0,
    minimum_latitude: float = 12.0,
    maximum_longitude: float = 78.0,
    maximum_latitude: float = 14.0,
) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "objectid": feature_id,
        "aquifer": "Mapped principal aquifer",
        "system": "Mapped aquifer system",
        "mbgl": None,
    }
    if properties:
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


def layer(
    *features: dict[str, Any],
    feature_type: HydrogeologyFeatureType = HydrogeologyFeatureType.AQUIFER,
    fields: HydrogeologyFieldMapping | None = None,
) -> dict[str, Any]:
    return OfficialHydrogeologyPolygonImporter().normalize(
        geojson(*features),
        source_id=SOURCE_ID,
        feature_type=feature_type,
        imported_at=IMPORTED_AT,
        dataset_version="reviewed deterministic fixture",
        source_layer=f"fixture {feature_type.value} layer",
        spatial_resolution="regional polygon fixture",
        fields=fields
        or HydrogeologyFieldMapping(
            record_id="objectid",
            aquifer_type="aquifer",
            aquifer_characteristics={"aquifer_system": "system"},
            aquifer_depth="mbgl",
        ),
    )


def cache(path: Path, *layers: dict[str, Any]) -> Path:
    combined = OfficialHydrogeologyPolygonImporter.combine(
        list(layers), imported_at=IMPORTED_AT
    )
    OfficialHydrogeologyPolygonImporter.write(combined, path)
    return path


def test_importer_preserves_separate_aquifer_attributes() -> None:
    normalized = layer(feature())

    assert normalized["recordCount"] == 1
    record = normalized["records"][0]
    assert record["featureType"] == "AQUIFER"
    assert record["sourceFeatureId"] == "1"
    assert record["geology"] is None
    assert record["geomorphology"] is None
    assert record["aquiferType"] == "Mapped principal aquifer"
    assert record["aquiferDepth"] is None
    assert record["aquiferCharacteristics"] == {
        "aquifer_system": "Mapped aquifer system"
    }


def test_invalid_spatial_feature_is_rejected() -> None:
    item = feature()
    item["geometry"]["coordinates"][0].pop()  # type: ignore[index]

    with pytest.raises(ValueError, match="ring must be closed"):
        layer(item)


def test_coordinate_inside_supported_feature_resolves(tmp_path: Path) -> None:
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(feature()))
    )

    result = provider.lookup(bengaluru_location())

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.aquifer_status is DataStatus.DATA_AVAILABLE
    assert result.information is not None
    assert result.information.aquifer_type == "Mapped principal aquifer"
    assert len(result.features) == 1


def test_coordinate_outside_supported_features_is_unavailable(tmp_path: Path) -> None:
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(feature()))
    )
    location = bengaluru_location().model_copy(
        update={"latitude": 20.0, "longitude": 80.0}
    )

    result = provider.lookup(location)

    assert result.status is DataStatus.UNSUPPORTED_LOCATION
    assert result.information is None
    assert result.features == []


def test_missing_optional_properties_remain_unknown(tmp_path: Path) -> None:
    item = feature(properties={"aquifer": None, "system": None, "mbgl": None})
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(item))
    )

    result = provider.lookup(bengaluru_location())

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.aquifer_status is DataStatus.DATA_UNAVAILABLE
    assert result.information is None
    assert result.features[0].aquifer_type is None
    assert result.features[0].aquifer_characteristics == {}


def test_independent_overlapping_layers_are_composed_without_collapsing_sources(
    tmp_path: Path,
) -> None:
    geology = layer(
        feature("geology-1", properties={"lithology": "Mapped lithology"}),
        feature_type=HydrogeologyFeatureType.GEOLOGY,
        fields=HydrogeologyFieldMapping(
            record_id="objectid", lithology="lithology"
        ),
    )
    aquifer = layer(feature("aquifer-1"))
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", geology, aquifer)
    )

    result = provider.lookup(bengaluru_location())

    assert result.geology_status is DataStatus.DATA_AVAILABLE
    assert result.aquifer_status is DataStatus.DATA_AVAILABLE
    assert result.information is not None
    assert result.information.lithology == "Mapped lithology"
    assert result.information.aquifer_type == "Mapped principal aquifer"
    assert len(result.features) == 2
    assert {item.source_feature_id for item in result.features} == {
        "geology-1",
        "aquifer-1",
    }


def test_overlapping_same_component_is_explicitly_ambiguous(tmp_path: Path) -> None:
    first = feature("aquifer-a")
    second = feature(
        "aquifer-b",
        properties={"aquifer": "Different mapped aquifer"},
        minimum_longitude=77.5,
        minimum_latitude=12.5,
        maximum_longitude=78.5,
        maximum_latitude=14.5,
    )
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(first, second))
    )
    location = bengaluru_location().model_copy(
        update={"latitude": 13.0, "longitude": 77.75}
    )

    result = provider.lookup(location)

    assert result.status is DataStatus.INSUFFICIENT_DATA
    assert result.aquifer_status is DataStatus.INSUFFICIENT_DATA
    assert result.information is None
    assert len(result.features) == 2
    assert "no value was selected" in result.message


def test_provenance_and_source_feature_id_survive_lookup(tmp_path: Path) -> None:
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(feature("source-42")))
    )

    result = provider.lookup(bengaluru_location())

    source_feature = result.features[0]
    assert source_feature.source_feature_id == "source-42"
    assert source_feature.dataset_name == "AquiferSystems_GSI ArcGIS Feature Service"
    assert source_feature.source_layer == "fixture AQUIFER layer"
    assert source_feature.source_organization == (
        "National Water Informatics Centre (NWIC) / Geological Survey of India (GSI)"
    )
    assert source_feature.provenance.source_ids == [SOURCE_ID]
    assert source_feature.provenance.retrieved_at == IMPORTED_AT


def test_field_mapping_rejects_cross_domain_assignment() -> None:
    with pytest.raises(ValueError, match="incompatible with AQUIFER"):
        layer(
            feature(),
            fields=HydrogeologyFieldMapping(
                record_id="objectid", geology="aquifer"
            ),
        )


def test_hydrogeology_lookup_flows_into_environmental_response(
    tmp_path: Path,
) -> None:
    provider = NormalizedOfficialHydrogeologyProvider(
        cache(tmp_path / "hydro.json", layer(feature()))
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
        hydrogeology_provider=provider,
    )

    profile = assessment.artificialRecharge.environmentalProfile
    assert profile is not None
    assert profile.hydrogeology.aquifer_status is DataStatus.DATA_AVAILABLE
    assert profile.hydrogeology.information is not None
    assert profile.hydrogeology.information.aquifer_type == (
        "Mapped principal aquifer"
    )
    assert profile.hydrogeology.features[0].source_feature_id == "1"
