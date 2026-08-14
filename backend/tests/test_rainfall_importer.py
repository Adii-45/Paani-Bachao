import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

from app.importers.imd_rainfall import (
    IMD_LAYER_URL,
    IMD_MONTHLY_SOURCE_ID,
    IMD_SOURCE_ID,
    MONTH_CODES,
    IMDDistrictRainfallImporter,
)


SOURCE_FIXTURE = """var json_Rainfallinmm_1 = {
  "type": "FeatureCollection",
  "features": [{
    "type": "Feature",
    "properties": {
      "STATE": "FIXTURE STATE",
      "DISTRICT": "FIXTURE DISTRICT",
      "ID": "fixture-1",
      "Rainfall (in mm)": 123.4
    },
    "geometry": {
      "type": "Polygon",
      "coordinates": [[[77, 12], [78, 12], [78, 13], [77, 13], [77, 12]]]
    }
  }]
};
"""


def test_imd_importer_preserves_source_and_spatial_metadata(tmp_path: Path) -> None:
    imported_at = datetime(2026, 8, 13, tzinfo=UTC)
    importer = IMDDistrictRainfallImporter()

    normalized = importer.normalize(SOURCE_FIXTURE, imported_at=imported_at)
    output = tmp_path / "rainfall.json.gz"
    importer.write(normalized, output)

    with gzip.open(output, "rt", encoding="utf-8") as source:
        stored = json.load(source)
    record = stored["records"][0]

    assert stored["record_count"] == 1
    assert stored["source_id"] == IMD_SOURCE_ID
    assert stored["reference_period"] == "1971-2020"
    assert record["rainfall_mm"] == 123.4
    assert record["source_url"] == IMD_LAYER_URL
    assert record["spatial_resolution"] == "IMD district polygon"
    assert record["bounding_box"] == [77.0, 12.0, 78.0, 13.0]
    assert record["geometry"]["type"] == "Polygon"


def test_imd_importer_preserves_all_monthly_normals_and_provenance() -> None:
    importer = IMDDistrictRainfallImporter()
    monthly_sources = {
        month: SOURCE_FIXTURE.replace("123.4", str(index + 1))
        for index, month in enumerate(MONTH_CODES)
    }

    normalized = importer.normalize(
        SOURCE_FIXTURE,
        imported_at=datetime(2026, 8, 13, tzinfo=UTC),
        monthly_source_texts=monthly_sources,
    )
    monthly = normalized["records"][0]["monthly_normal"]

    assert monthly["values_mm"] == list(range(1, 13))
    assert monthly["reference_period"] == "1971-2020"
    assert monthly["source_id"] == IMD_MONTHLY_SOURCE_ID
    assert len(monthly["source_urls"]) == 12
    assert len(monthly["source_records"]) == 12
    assert normalized["monthly_source_sha256"].keys() == set(MONTH_CODES)


def test_imd_importer_requires_all_twelve_monthly_layers() -> None:
    importer = IMDDistrictRainfallImporter()

    try:
        importer.normalize(
            SOURCE_FIXTURE,
            imported_at=datetime(2026, 8, 13, tzinfo=UTC),
            monthly_source_texts={"jan": SOURCE_FIXTURE},
        )
    except ValueError as exc:
        assert "Exactly twelve" in str(exc)
    else:
        raise AssertionError("Importer accepted an incomplete monthly dataset")


def test_importer_rejects_missing_rainfall_value() -> None:
    importer = IMDDistrictRainfallImporter()
    incomplete = SOURCE_FIXTURE.replace('"Rainfall (in mm)": 123.4', '"unused": 1')

    try:
        importer.normalize(incomplete, imported_at=datetime(2026, 8, 13, tzinfo=UTC))
    except ValueError as exc:
        assert "missing required source fields" in str(exc)
    else:
        raise AssertionError("Importer accepted an incomplete IMD feature")


def test_importer_rejects_malformed_rainfall_value() -> None:
    importer = IMDDistrictRainfallImporter()
    malformed = SOURCE_FIXTURE.replace(
        '"Rainfall (in mm)": 123.4', '"Rainfall (in mm)": "not-a-number"'
    )

    try:
        importer.normalize(malformed, imported_at=datetime(2026, 8, 13, tzinfo=UTC))
    except ValueError:
        pass
    else:
        raise AssertionError("Importer accepted a malformed IMD rainfall value")


def test_importer_rejects_negative_rainfall_instead_of_changing_units() -> None:
    importer = IMDDistrictRainfallImporter()
    negative = SOURCE_FIXTURE.replace("123.4", "-1")

    try:
        importer.normalize(negative, imported_at=datetime(2026, 8, 13, tzinfo=UTC))
    except ValueError as exc:
        assert "greater than or equal to 0" in str(exc)
    else:
        raise AssertionError("Importer accepted negative rainfall")
