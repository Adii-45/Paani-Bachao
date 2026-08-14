from dataclasses import dataclass

from .feasibility import FeasibilityResult, FeasibilityStatus
from .standard_designs import design_row, normalize_formation


SOURCE_ID = "CGWB_DELHI_STANDARD_DESIGNS"


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


def _is_delhi(state: str | None) -> bool:
    if not state:
        return False
    normalized = state.casefold().replace("national capital territory of", "").strip()
    return normalized in {"delhi", "nct delhi", "nct of delhi"}


def select_structure(
    feasibility: FeasibilityResult,
    *,
    state: str | None = None,
    geology: str | None = None,
    lithology: str | None = None,
    groundwater_depth_m_bgl: float | None = None,
    building_has_basement: bool | None = None,
    roof_area_m2: float | None = None,
    available_ground_area_m2: float | None = None,
) -> StructureSelectionResult:
    """Apply only the reviewed CGWB Delhi standard-design applicability rules."""

    if feasibility.status in {
        FeasibilityStatus.NOT_ELIGIBLE,
        FeasibilityStatus.INSUFFICIENT_DATA,
    }:
        return StructureSelectionResult(
            status="INSUFFICIENT_DATA_FOR_SELECTION",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=(),
            missing_inputs=feasibility.reasons,
            source_ids=(SOURCE_ID,),
        )
    if not _is_delhi(state):
        return StructureSelectionResult(
            status="UNSUPPORTED_LOCATION_FOR_SELECTION",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=(),
            missing_inputs=(
                "a reviewed, location-specific structure-selection method; the installed "
                "CGWB standard-design table applies only to NCT Delhi",
            ),
            source_ids=(SOURCE_ID,),
        )

    formation = normalize_formation(geology, lithology)
    missing: list[str] = []
    if formation is None:
        missing.append("reviewed formation classification (alluvial or hard rock)")
    if groundwater_depth_m_bgl is None:
        missing.append("post-monsoon groundwater depth")
    if building_has_basement is None:
        missing.append("whether the building has a basement")
    if roof_area_m2 is None:
        missing.append("roof catchment area")
    if available_ground_area_m2 is None:
        missing.append("available construction footprint")
    if missing:
        return StructureSelectionResult(
            status="INSUFFICIENT_DATA_FOR_SELECTION",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=(),
            missing_inputs=tuple(missing),
            source_ids=(SOURCE_ID,),
        )

    rejected: list[RejectedStructure] = []
    structure: str | None = None
    reasons: list[str] = []
    if 5 < groundwater_depth_m_bgl <= 15:
        if formation != "ALLUVIAL":
            rejected.append(
                RejectedStructure(
                    structure="RECHARGE_TRENCH",
                    reason=(
                        "The Delhi trench-without-well design is limited to alluvial formation "
                        "for groundwater depth greater than 5 m and up to 15 m bgl."
                    ),
                    source_ids=(SOURCE_ID,),
                )
            )
        elif building_has_basement:
            rejected.append(
                RejectedStructure(
                    structure="RECHARGE_TRENCH",
                    reason=(
                        "The CGWB Delhi design directs buildings with basements to rainwater "
                        "storage rather than this recharge-trench design."
                    ),
                    source_ids=(SOURCE_ID,),
                )
            )
        else:
            structure = "RECHARGE_TRENCH"
            reasons.extend(
                (
                    "The site is in NCT Delhi and the reviewed formation is alluvial.",
                    "Post-monsoon groundwater depth is greater than 5 m and not more than 15 m bgl.",
                    "The building is reported not to have a basement.",
                )
            )
    elif groundwater_depth_m_bgl > 15 and formation in {"ALLUVIAL", "HARD_ROCK"}:
        structure = "TRENCH_WITH_RECHARGE_WELL"
        reasons.extend(
            (
                "The site is in NCT Delhi with alluvial or hard-rock formation.",
                "Post-monsoon groundwater depth is greater than 15 m bgl.",
            )
        )
    else:
        rejected.extend(
            (
                RejectedStructure(
                    structure="RECHARGE_TRENCH",
                    reason="The groundwater-depth/formation conditions do not match the Delhi trench table.",
                    source_ids=(SOURCE_ID,),
                ),
                RejectedStructure(
                    structure="TRENCH_WITH_RECHARGE_WELL",
                    reason="The groundwater-depth/formation conditions do not match the Delhi trench-with-well table.",
                    source_ids=(SOURCE_ID,),
                ),
            )
        )

    if structure is None:
        return StructureSelectionResult(
            status="NO_APPLICABLE_SOURCE_BACKED_STRUCTURE",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=tuple(rejected),
            missing_inputs=(),
            source_ids=(SOURCE_ID,),
        )

    row = design_row(structure, roof_area_m2)
    if row is None:
        rejected.append(
            RejectedStructure(
                structure=structure,
                reason="The published CGWB standard-design table covers roof areas only up to 500 m².",
                source_ids=(SOURCE_ID,),
            )
        )
        return StructureSelectionResult(
            status="NO_APPLICABLE_SOURCE_BACKED_STRUCTURE",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=tuple(rejected),
            missing_inputs=(),
            source_ids=(SOURCE_ID,),
        )

    required_footprint = row["lengthM"] * row["widthM"]
    if required_footprint > available_ground_area_m2:
        rejected.append(
            RejectedStructure(
                structure=structure,
                reason=(
                    f"Published internal footprint is {required_footprint:.2f} m², "
                    f"which exceeds the reported {available_ground_area_m2:.2f} m²."
                ),
                source_ids=(SOURCE_ID,),
            )
        )
        return StructureSelectionResult(
            status="NO_STRUCTURE_FITS_AVAILABLE_AREA",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=tuple(rejected),
            missing_inputs=(),
            source_ids=(SOURCE_ID,),
        )

    return StructureSelectionResult(
        status=(
            "CONDITIONAL_RECOMMENDATION"
            if feasibility.status is FeasibilityStatus.CONDITIONALLY_ELIGIBLE
            else "RECOMMENDED"
        ),
        recommended_structure=structure,
        alternative_structures=(),
        selection_reasons=tuple(reasons),
        rejected_structures=tuple(rejected),
        missing_inputs=(),
        source_ids=(SOURCE_ID,),
    )
