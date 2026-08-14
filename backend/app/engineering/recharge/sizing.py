from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from .standard_designs import design_row, load_delhi_standard_designs
from .structure_selection import StructureSelectionResult


SOURCE_ID = "CGWB_DELHI_STANDARD_DESIGNS"
KSCST_SOURCE_ID = "KSCST_RWH_TANK_WELL_SIZES"
KSCST_TABLE_PATH = Path(__file__).resolve().parents[2] / "data" / "source_backed" / "kscst_residential_recharge_well_table.json"
SQUARE_METRES_PER_SQUARE_FOOT = 0.09290304
METRES_PER_FOOT = 0.3048


def _kscst_table_row(roof_area_m2: float, open_area_m2: float) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    payload = json.loads(KSCST_TABLE_PATH.read_text(encoding="utf-8"))
    roof_sq_ft = roof_area_m2 / SQUARE_METRES_PER_SQUARE_FOOT
    open_sq_ft = open_area_m2 / SQUARE_METRES_PER_SQUARE_FOOT
    for row in payload["rows"]:
        if abs(roof_sq_ft - row["roofAreaSqFt"]) <= 0.01 and abs(open_sq_ft - row["openAreaSqFt"]) <= 0.01:
            return row, payload
    return None, payload


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
        source_ids=selection.source_ids,
        method_id=(
            "CGWB_DELHI_STANDARD_RTRWH_DESIGNS"
            if SOURCE_ID in selection.source_ids
            else "NOT_APPLICABLE"
        ),
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

    if selection.recommended_structure == "RECHARGE_WELL" and KSCST_SOURCE_ID in selection.source_ids:
        missing: list[str] = []
        if roof_area_m2 is None:
            missing.append("roof catchment area")
        if available_ground_area_m2 is None:
            missing.append("available construction footprint")
        if available_recharge_water_litres is None or available_recharge_water_litres <= 0:
            missing.append("positive recharge-available overflow")
        row = None
        table = None
        if roof_area_m2 is not None and available_ground_area_m2 is not None:
            row, table = _kscst_table_row(roof_area_m2, available_ground_area_m2)
            if row is None:
                missing.append("roof and open areas matching a reviewed published KSCST square-foot table row")
        if missing:
            return StructureSizingResult(
                status="INSUFFICIENT_DATA_FOR_SIZING",
                structure_type="RECHARGE_WELL",
                dimensions=None,
                required_footprint_m2=None,
                filter_media=(),
                design_inputs={},
                assumptions=(),
                field_verification_required=("A qualified professional must confirm the aquifer intake zone and final well depth.",),
                missing_inputs=tuple(missing),
                source_ids=selection.source_ids,
                method_id="KSCST_RESIDENTIAL_RWH_WELL_TABLE",
                message="The property inputs do not match an exact row in the published KSCST table.",
            )

        design_volume_litres = row["designVolumeLitres"]
        options = []
        for diameter_ft, depth_key in ((3, "depth3FtDiameterFt"), (4, "depth4FtDiameterFt"), (5, "depth5FtDiameterFt")):
            diameter = diameter_ft * METRES_PER_FOOT
            footprint = 3.141592653589793 * (diameter / 2) ** 2
            if footprint <= available_ground_area_m2:
                options.append({
                    "diameterM": round(diameter, 2),
                    "publishedCalculatedDepthM": round(row[depth_key] * METRES_PER_FOOT, 2),
                    "minimumDesignDepthM": round(max(table["minimumWellDepthFt"], row[depth_key]) * METRES_PER_FOOT, 2),
                    "footprintM2": round(footprint, 2),
                })
        if not options:
            return StructureSizingResult(
                status="DOES_NOT_FIT_AVAILABLE_AREA",
                structure_type="RECHARGE_WELL",
                dimensions=None,
                required_footprint_m2=0.66,
                filter_media=(), design_inputs={}, assumptions=(),
                field_verification_required=(), missing_inputs=(),
                source_ids=selection.source_ids,
                method_id="KSCST_RESIDENTIAL_RWH_WELL_TABLE",
                message="Even the smallest published well diameter exceeds the reported open area.",
            )
        return StructureSizingResult(
            status="PARTIAL_INDICATIVE_DESIGN",
            structure_type="RECHARGE_WELL",
            dimensions={
                "designStorageVolumeLitres": design_volume_litres,
                "wellOptions": options,
                "finalAquiferIntakeDepthM": None,
            },
            required_footprint_m2=min(item["footprintM2"] for item in options),
            filter_media=("Use reviewed filter/media details appropriate to the final professionally designed installation.",),
            design_inputs={
                "roofAreaM2": roof_area_m2,
                "openAreaM2": available_ground_area_m2,
                "availableRechargeWaterLitresPerYear": available_recharge_water_litres,
            },
            assumptions=(
                "The design volume and diameter/depth choices are transcribed from an exact published KSCST square-foot table row; values are not interpolated.",
                "The tabulated geometric depth is not an aquifer intake or borehole termination depth.",
            ),
            field_verification_required=(
                "Perform a property infiltration/percolation test.",
                "Confirm current groundwater level and a suitable aquifer intake zone before finalizing well depth.",
                "Obtain professional design review before connecting to an existing borewell.",
            ),
            missing_inputs=("field-confirmed aquifer intake depth",),
            source_ids=selection.source_ids,
            method_id="KSCST_RESIDENTIAL_RWH_WELL_TABLE",
            message="KSCST table options are available; final aquifer intake depth remains intentionally unset pending field investigation.",
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
    dimension_prefix = (
        "trench"
        if selection.recommended_structure == "RECHARGE_TRENCH"
        else "chamber"
    )
    dimensions: dict[str, Any] = {
        f"{dimension_prefix}LengthM": row["lengthM"],
        f"{dimension_prefix}WidthM": row["widthM"],
        f"{dimension_prefix}DepthM": row["depthM"],
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
            return StructureSizingResult(
                status="PARTIAL_INDICATIVE_DESIGN",
                structure_type=selection.recommended_structure,
                dimensions={**dimensions, "finalWellTerminationDepthM": None},
                required_footprint_m2=footprint,
                filter_media=tuple(rules["filterMedia"]),
                design_inputs={
                    "roofAreaM2": roof_area_m2,
                    "availableRechargeWaterLitresPerYear": available_recharge_water_litres,
                },
                assumptions=("The chamber dimensions are copied from the applicable CGWB table; the recharge-well depth is not inferred.",),
                field_verification_required=tuple([*verification, "Confirm a granular or fractured intake zone and final well termination through field investigation."]),
                missing_inputs=tuple(well_missing),
                source_ids=(SOURCE_ID,),
                method_id="CGWB_DELHI_STANDARD_RTRWH_DESIGNS",
                message="The published chamber can be shown, but recharge-well depth remains unavailable until field-confirmed intake evidence exists.",
            )
        dimensions["indicativeWellTerminationDepthMinM"] = round(
            post_monsoon_groundwater_depth_m - 3, 2
        )
        dimensions["indicativeWellTerminationDepthMaxM"] = round(
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
