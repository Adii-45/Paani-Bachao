import gzip
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..domain.environment import RainfallRecord
from ..provenance.registry import source_registry

IMD_SOURCE_ID = "IMD_DISTRICT_ANNUAL_NORMALS_1971_2020"
IMD_PRODUCT_TITLE = "All India Districtwise Rainfall Normals (1971-2020) Annual"
IMD_PRODUCT_PAGE = "https://www.imdpune.gov.in/climinfo/season/ann/index.html"
IMD_LAYER_URL = (
    "https://www.imdpune.gov.in/climinfo/season/ann/layers/Rainfallinmm_1.js"
)


def _bounding_box(geometry: dict[str, Any]) -> tuple[float, float, float, float]:
    points: list[list[float]] = []

    def collect(value: Any) -> None:
        if (
            isinstance(value, list)
            and len(value) >= 2
            and isinstance(value[0], (int, float))
            and isinstance(value[1], (int, float))
        ):
            points.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(geometry.get("coordinates"))
    if not points:
        raise ValueError("IMD feature contains no geometry coordinates.")
    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    return min(longitudes), min(latitudes), max(longitudes), max(latitudes)


class IMDDistrictRainfallImporter:
    """Normalize the official IMD annual district-normal GeoJSON web layer."""

    def normalize(self, source_text: str, *, imported_at: datetime) -> dict[str, Any]:
        if IMD_SOURCE_ID not in source_registry():
            raise ValueError(f"Unknown source ID: {IMD_SOURCE_ID}")
        try:
            payload = json.loads(
                source_text[source_text.index("{") : source_text.rindex("}") + 1]
            )
        except (ValueError, json.JSONDecodeError) as exc:
            raise ValueError("The IMD layer is not valid wrapped GeoJSON.") from exc
        if payload.get("type") != "FeatureCollection":
            raise ValueError("The IMD layer is not a GeoJSON FeatureCollection.")

        records: list[dict[str, Any]] = []
        for feature in payload.get("features", []):
            properties = feature.get("properties") or {}
            geometry = feature.get("geometry")
            state = properties.get("STATE")
            district = properties.get("DISTRICT")
            feature_id = properties.get("ID")
            rainfall = properties.get("Rainfall (in mm)")
            if not state or not district or feature_id is None or rainfall is None:
                raise ValueError("An IMD feature is missing required source fields.")
            if not isinstance(geometry, dict) or geometry.get("type") not in {
                "Polygon",
                "MultiPolygon",
            }:
                raise ValueError("An IMD feature has unsupported or missing geometry.")

            record = RainfallRecord(
                recordId=f"imd-annual-normal-1971-2020-{feature_id}",
                locationName=str(district),
                state=str(state),
                district=str(district),
                rainfallMm=float(rainfall),
                statisticType="LONG_PERIOD_NORMAL_ANNUAL",
                referencePeriod="1971-2020",
                spatialResolution="IMD district polygon",
                sourceId=IMD_SOURCE_ID,
                sourceName="India Meteorological Department (IMD)",
                sourceUrl=IMD_LAYER_URL,
                sourceRecord=(
                    f"Feature ID {feature_id}; STATE={state}; DISTRICT={district}; "
                    "field=Rainfall (in mm)"
                ),
                datasetVersion="1971-2020 annual district normals",
                retrievedAt=imported_at,
                boundingBox=_bounding_box(geometry),
                geometry=geometry,
            )
            records.append(record.model_dump(mode="json", by_alias=False))

        if not records:
            raise ValueError("The IMD layer contains no rainfall records.")
        records.sort(key=lambda item: (str(item["state"]), str(item["district"])))
        return {
            "dataset_status": "DATA_AVAILABLE",
            "source_id": IMD_SOURCE_ID,
            "source_name": "India Meteorological Department (IMD)",
            "dataset_title": IMD_PRODUCT_TITLE,
            "dataset_version": "1971-2020 annual district normals",
            "reference_period": "1971-2020",
            "spatial_resolution": "district polygon",
            "source_url": IMD_LAYER_URL,
            "product_page": IMD_PRODUCT_PAGE,
            "source_sha256": hashlib.sha256(source_text.encode()).hexdigest(),
            "imported_at": imported_at.isoformat(),
            "record_count": len(records),
            "records": records,
        }

    def write(self, normalized: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(
            normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode()
        if output_path.suffix == ".gz":
            with output_path.open("wb") as destination:
                with gzip.GzipFile(fileobj=destination, mode="wb", mtime=0) as compressed:
                    compressed.write(serialized)
            return
        output_path.write_bytes(serialized + b"\n")
