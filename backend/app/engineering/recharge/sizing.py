from dataclasses import dataclass
from typing import Any

from .standard_designs import design_row, load_delhi_standard_designs
from .structure_selection import StructureSelectionResult


SOURCE_ID = "CGWB_DELHI_STANDARD_DESIGNS"


@dataclass(frozen=True)
class StructureSizingResult:
    status: str
    structure_type: str | None
    dimensions: dict[str, Any] | None
    required_footprint_m2: float | None
    filter_media: tuple[str, ...]
    design_inputs: dict[str, Any]
    assumptions: tuple[str, ...]
    field_verification_required: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    method_id: str
    message: str


def _unavailable(
    selection: StructureSelectionResult,
    missing: tuple[str, ...],
    message: str,
) -> StructureSizingResult:
    return StructureSizingResult(
        status="INSUFFICIENT_DATA_FOR_SIZING",
        structure_type=selection.recommended_structure,
        dimensions=None,
        required_footprint_m2=None,
        filter_media=(),
        design_inputs={},
        assumptions=(),
        field_verification_required=(),
        missing_inputs=missing,
        source_ids=(SOURCE_ID,),
        method_id="CGWB_DELHI_STANDARD_RTRWH_DESIGNS",
        message=message,
    )


def assess_structure_size(
    selection: StructureSelectionResult,
    *,
    roof_area_m2: float | None = None,
    available_ground_area_m2: float | None = None,
    available_recharge_water_litres: float | None = None,
    post_monsoon_groundwater_depth_m: float | None = None,
    aquifer_intake_zone_verified: bool = False,
) -> StructureSizingResult:
    """Return only dimensions published by the applicable CGWB Delhi design."""

    if selection.recommended_structure is None:
        missing = selection.missing_inputs or (
            "a structure selected through an applicable source-backed method",
        )
        return _unavailable(
            selection,
            missing,
            "Dimensions are unavailable because no structure was selected.",
        )
    missing: list[str] = []
    if roof_area_m2 is None:
        missing.append("roof catchment area")
    if available_ground_area_m2 is None:
        missing.append("available construction footprint")
    if available_recharge_water_litres is None:
        missing.append("recharge-available overflow from the storage water balance")
    elif available_recharge_water_litres <= 0:
        missing.append("positive recharge-available overflow")
    if missing:
        return _unavailable(
            selection,
            tuple(missing),
            "The selected structure cannot be sized until its hydraulic and footprint inputs are available.",
        )

    row = design_row(selection.recommended_structure, roof_area_m2)
    if row is None:
        return _unavailable(
            selection,
            ("roof area within the published CGWB range of up to 500 m²",),
            "The published Delhi standard-design table does not cover this roof area.",
        )
    footprint = round(row["lengthM"] * row["widthM"], 2)
    if footprint > available_ground_area_m2:
        return StructureSizingResult(
            status="DOES_NOT_FIT_AVAILABLE_AREA",
            structure_type=selection.recommended_structure,
            dimensions=None,
            required_footprint_m2=footprint,
            filter_media=(),
            design_inputs={"availableGroundAreaM2": available_ground_area_m2},
            assumptions=(),
            field_verification_required=(),
            missing_inputs=(),
            source_ids=(SOURCE_ID,),
            method_id="CGWB_DELHI_STANDARD_RTRWH_DESIGNS",
            message="The published internal footprint exceeds the reported open ground area.",
        )

    rules = load_delhi_standard_designs()
    dimensions: dict[str, Any] = {
        "lengthM": row["lengthM"],
        "widthM": row["widthM"],
        "depthM": row["depthM"],
    }
    verification = [
        "Confirm site hydrogeology and post-monsoon groundwater level.",
        "Complete water-quality and contamination-risk review.",
        "Complete a property-level infiltration/percolation test.",
        "Inspect utilities, foundations and structural loads before construction.",
        "Confirm permissions and applicable local rules.",
    ]
    if selection.recommended_structure == "TRENCH_WITH_RECHARGE_WELL":
        well_missing: list[str] = []
        if post_monsoon_groundwater_depth_m is None:
            well_missing.append("post-monsoon groundwater depth for recharge-well termination")
        if not aquifer_intake_zone_verified:
            well_missing.append("verified granular or fractured intake zone")
        if well_missing:
            return _unavailable(
                selection,
                tuple(well_missing),
                "The chamber table is available, but a complete trench-with-well design requires field-confirmed well termination and intake-zone evidence.",
            )
        dimensions["rechargeWellDepthMinM"] = round(
            post_monsoon_groundwater_depth_m - 3, 2
        )
        dimensions["rechargeWellDepthMaxM"] = round(
            post_monsoon_groundwater_depth_m - 2, 2
        )
        verification.append(
            "Place the slotted pipe only against the field-confirmed granular or fractured zone."
        )

    basis = rules["publishedDesignBasis"]
    return StructureSizingResult(
        status="INDICATIVE_DESIGN_AVAILABLE",
        structure_type=selection.recommended_structure,
        dimensions=dimensions,
        required_footprint_m2=footprint,
        filter_media=tuple(rules["filterMedia"]),
        design_inputs={
            "roofAreaM2": roof_area_m2,
            "availableRechargeWaterLitresPerYear": available_recharge_water_litres,
            "publishedHighestRainfallIntensityMPerHour": basis[
                "highestRainfallIntensityMPerHour"
            ],
            "publishedRunoffCoefficient": basis["runoffCoefficient"],
            "publishedNormalMonsoonRainfallM": basis["normalMonsoonRainfallM"],
        },
        assumptions=(
            "Dimensions are selected from the published roof-area band, not interpolated.",
            "The Delhi table's published storm/rainfall/coefficient basis is reported separately and is not substituted into annual RTRWH yield.",
            "The design is indicative; CGWB states the actual design depends on site conditions.",
        ),
        field_verification_required=tuple(verification),
        missing_inputs=(),
        source_ids=(SOURCE_ID,),
        method_id="CGWB_DELHI_STANDARD_RTRWH_DESIGNS",
        message=(
            "Indicative dimensions come directly from the applicable CGWB Delhi standard-design roof-area band."
        ),
    )
