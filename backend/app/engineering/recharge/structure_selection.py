from dataclasses import dataclass

from .feasibility import FeasibilityResult, FeasibilityStatus


@dataclass(frozen=True)
class RejectedStructure:
    structure: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class StructureSelectionResult:
    status: str
    recommended_structure: str | None
    alternative_structures: tuple[str, ...]
    selection_reasons: tuple[str, ...]
    rejected_structures: tuple[RejectedStructure, ...]
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]


def select_structure(feasibility: FeasibilityResult) -> StructureSelectionResult:
    if feasibility.status is not FeasibilityStatus.ELIGIBLE:
        return StructureSelectionResult(
            status="INSUFFICIENT_DATA_FOR_SELECTION",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=(),
            missing_inputs=feasibility.reasons,
            source_ids=(
                "CGWB_MANUAL_AR_2007",
                "CGWB_GUIDE_AR",
                "BIS_IS_15792_2008",
            ),
        )
    return StructureSelectionResult(
        status="RESEARCH_REQUIRED",
        recommended_structure=None,
        alternative_structures=(),
        selection_reasons=(),
        rejected_structures=(),
        missing_inputs=("an applicable source-backed structure-selection rule",),
        source_ids=("CGWB_MANUAL_AR_2007", "BIS_IS_15792_2008"),
    )
