from app.engineering.recharge.sizing import assess_structure_size
from app.engineering.recharge.structure_selection import StructureSelectionResult
from app.engineering.rtrwh.storage import assess_storage_size


def test_storage_does_not_use_annual_volume_as_tank_size() -> None:
    result = assess_storage_size()

    assert result.status.value == "INSUFFICIENT_DATA_FOR_SIZING"
    assert result.recommended_litres is None
    assert "event rainfall or rainfall distribution" in result.missing_inputs
    assert "CGWB_MANUAL_AR_2007" in result.source_ids


def test_ar_dimensions_are_not_fabricated_without_structure_and_inputs() -> None:
    selection = StructureSelectionResult(
        status="INSUFFICIENT_DATA_FOR_SELECTION",
        recommended_structure=None,
        alternative_structures=(),
        selection_reasons=(),
        rejected_structures=(),
        missing_inputs=("hydrogeology", "infiltration"),
        source_ids=("CGWB_MANUAL_AR_2007",),
    )

    result = assess_structure_size(selection)

    assert result.status == "INSUFFICIENT_DATA_FOR_SIZING"
    assert result.dimensions is None
    assert result.missing_inputs == ("hydrogeology", "infiltration")
