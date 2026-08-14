from dataclasses import dataclass

from .feasibility import FeasibilityResult, FeasibilityStatus
from .standard_designs import design_row, normalize_formation


DELHI_SOURCE_ID = "CGWB_DELHI_STANDARD_DESIGNS"
BENGALURU_SOURCE_IDS = (
    "CGWB_BENGALURU_NAQUIM_2025",
    "KSCST_RWH_TANK_WELL_SIZES",
)


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
    regional_methodology_id: str | None = None,
) -> StructureSelectionResult:
    """Apply only a reviewed methodology identified by intersecting source data."""

    source_ids = (
        BENGALURU_SOURCE_IDS
        if regional_methodology_id == "BENGALURU_NAQUIM_URBAN_CORE"
        else (DELHI_SOURCE_ID,)
        if regional_methodology_id == "DELHI_CGWB_STANDARD"
        else ()
    )

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
            source_ids=source_ids,
        )
    if regional_methodology_id == "BENGALURU_NAQUIM_URBAN_CORE":
        missing = []
        if groundwater_depth_m_bgl is None:
            missing.append("reviewed post-monsoon groundwater depth")
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
                source_ids=source_ids,
            )
        if groundwater_depth_m_bgl < 3:
            return StructureSelectionResult(
                status="NO_APPLICABLE_SOURCE_BACKED_STRUCTURE",
                recommended_structure=None,
                alternative_structures=(),
                selection_reasons=(),
                rejected_structures=(RejectedStructure(
                    structure="RECHARGE_WELL",
                    reason="The reviewed post-monsoon groundwater level is shallower than the CGWB recharge exclusion threshold.",
                    source_ids=source_ids,
                ),),
                missing_inputs=(),
                source_ids=source_ids,
            )
        # CGWB Bengaluru NAQUIM identifies rooftop recharge pits/wells/trenches
        # for the urban core. KSCST publishes a residential recharge-well table.
        # Both remain conditional because property infiltration and the final
        # aquifer intake zone require field verification.
        return StructureSelectionResult(
            status="CONDITIONAL_RECOMMENDATION",
            recommended_structure="RECHARGE_WELL",
            alternative_structures=("RECHARGE_PIT",),
            selection_reasons=(
                "The resolved site intersects the CGWB Bengaluru urban-core methodology area.",
                "CGWB identifies rooftop recharge pits/wells and percolation trenches for this urban setting.",
                "KSCST provides a residential recharge-well sizing table for the reported roof and open areas.",
                "Final choice and intake depth require field infiltration and hydrogeological verification.",
            ),
            rejected_structures=(),
            missing_inputs=(),
            source_ids=source_ids,
        )

    if regional_methodology_id != "DELHI_CGWB_STANDARD" or not _is_delhi(state):
        return StructureSelectionResult(
            status="UNSUPPORTED_LOCATION_FOR_SELECTION",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=(),
            missing_inputs=(
                "a reviewed, location-specific structure-selection method intersecting the resolved coordinate",
            ),
            source_ids=source_ids,
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
            source_ids=source_ids,
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
                    source_ids=source_ids,
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
                    source_ids=source_ids,
                )
            )
        else:
            structure = "RECHARGE_TRENCH"
            rejected.append(
                RejectedStructure(
                    structure="TRENCH_WITH_RECHARGE_WELL",
                    reason=(
                        "The reviewed post-monsoon groundwater depth is not greater "
                        "than 15 m bgl, which is required by the Delhi trench-with-"
                        "recharge-well table."
                    ),
                    source_ids=source_ids,
                )
            )
            reasons.extend(
                (
                    "The site is in NCT Delhi and the reviewed formation is alluvial.",
                    "Post-monsoon groundwater depth is greater than 5 m and not more than 15 m bgl.",
                    "The building is reported not to have a basement.",
                )
            )
    elif groundwater_depth_m_bgl > 15 and formation in {"ALLUVIAL", "HARD_ROCK"}:
        structure = "TRENCH_WITH_RECHARGE_WELL"
        rejected.append(
            RejectedStructure(
                structure="RECHARGE_TRENCH",
                reason=(
                    "The reviewed post-monsoon groundwater depth exceeds the Delhi "
                    "trench-without-well table's 15 m bgl upper limit."
                ),
                source_ids=source_ids,
            )
        )
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
                    source_ids=source_ids,
                ),
                RejectedStructure(
                    structure="TRENCH_WITH_RECHARGE_WELL",
                    reason="The groundwater-depth/formation conditions do not match the Delhi trench-with-well table.",
                    source_ids=source_ids,
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
            source_ids=source_ids,
        )

    row = design_row(structure, roof_area_m2)
    if row is None:
        rejected.append(
            RejectedStructure(
                structure=structure,
                reason="The published CGWB standard-design table covers roof areas only up to 500 m².",
                source_ids=source_ids,
            )
        )
        return StructureSelectionResult(
            status="NO_APPLICABLE_SOURCE_BACKED_STRUCTURE",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=tuple(rejected),
            missing_inputs=(),
            source_ids=source_ids,
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
                source_ids=source_ids,
            )
        )
        return StructureSelectionResult(
            status="NO_STRUCTURE_FITS_AVAILABLE_AREA",
            recommended_structure=None,
            alternative_structures=(),
            selection_reasons=(),
            rejected_structures=tuple(rejected),
            missing_inputs=(),
            source_ids=source_ids,
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
        source_ids=source_ids,
    )
