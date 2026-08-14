from app.provenance.models import DataStatus
from app.providers.runoff import SourceBackedRunoffCoefficientProvider


def test_repository_keeps_unsupported_material_unavailable() -> None:
    result = SourceBackedRunoffCoefficientProvider().lookup("OTHER")

    assert result.status is DataStatus.DATA_UNAVAILABLE
    assert result.record is None


def test_cgwb_table_7_2_material_values_are_traceable() -> None:
    # CGWB Manual (2007), Table 7.2, document page 118.
    expected = {"RCC": 0.7, "TILES": 0.75, "METAL": 0.9}

    for roof_type, coefficient in expected.items():
        result = SourceBackedRunoffCoefficientProvider().lookup(roof_type)
        assert result.status is DataStatus.DATA_AVAILABLE
        assert result.record is not None
        assert result.record.value_range.selected_value == coefficient
        assert result.record.source_ids == ["CGWB_MANUAL_AR_2007"]
        assert result.record.provenance.source_record == "Table 7.2, document page 118"
