from dataclasses import dataclass

from .structure_selection import StructureSelectionResult


@dataclass(frozen=True)
class StructureSizingResult:
    status: str
    dimensions: dict[str, float] | None
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    message: str


def assess_structure_size(selection: StructureSelectionResult) -> StructureSizingResult:
    missing = selection.missing_inputs or (
        "structure-specific design inputs and an applicable sizing method",
    )
    return StructureSizingResult(
        status="INSUFFICIENT_DATA_FOR_SIZING",
        dimensions=None,
        missing_inputs=missing,
        source_ids=("CGWB_MANUAL_AR_2007", "BIS_IS_15792_2008"),
        message=(
            "Numeric dimensions are unavailable until a technically applicable structure "
            "and all inputs required by its source-backed sizing method are known."
        ),
    )
