from dataclasses import dataclass
from enum import Enum


class FeasibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class CriterionStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    REQUIRES_VERIFICATION = "REQUIRES_VERIFICATION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


class WaterQualityStatus(str, Enum):
    VERIFIED_ACCEPTABLE = "VERIFIED_ACCEPTABLE"
    NOT_VERIFIED = "NOT_VERIFIED"
    UNSUITABLE = "UNSUITABLE"


@dataclass(frozen=True)
class FeasibilityCriterion:
    criterion: str
    result: CriterionStatus
    observed_value: str | float | None
    required_condition: str
    reason: str
    source_ids: tuple[str, ...]


@dataclass(frozen=True)
class FeasibilityResult:
    status: FeasibilityStatus
    criteria: tuple[FeasibilityCriterion, ...]
    reasons: tuple[str, ...]
    conditions_passed: tuple[str, ...]
    conditions_failed: tuple[str, ...]
    conditions_requiring_verification: tuple[str, ...]
    missing_data: tuple[str, ...]
    field_tests_recommended: tuple[str, ...]
    source_ids: tuple[str, ...]


def _is_post_monsoon(season: str | None) -> bool:
    if not season:
        return False
    normalized = season.upper().replace("-", "_").replace(" ", "_")
    return "POST_MONSOON" in normalized or "NOVEMBER" in normalized


def evaluate_feasibility(
    *,
    groundwater_depth_m_bgl: float | None,
    groundwater_has_observation_metadata: bool,
    groundwater_observation_season: str | None = None,
    recharge_water_litres: float | None = None,
    has_infiltration_evidence: bool,
    infiltration_is_property_measured: bool = False,
    has_hydrogeology_evidence: bool,
    water_quality_status: WaterQualityStatus = WaterQualityStatus.NOT_VERIFIED,
    available_ground_area_m2: float,
    groundwater_reason: str | None = None,
    infiltration_reason: str | None = None,
    hydrogeology_reason: str | None = None,
) -> FeasibilityResult:
    """Evaluate explicit evidence and exclusions without a numeric score."""

    if recharge_water_litres is None:
        recharge_criterion = FeasibilityCriterion(
            criterion="recharge_water_quantity",
            result=CriterionStatus.INSUFFICIENT_DATA,
            observed_value=None,
            required_condition="A completed storage water balance with positive overflow.",
            reason="A completed storage/overflow water balance is unavailable.",
            source_ids=("CGWB_MANUAL_AR_2007", "IRICEN_RWH_2022"),
        )
    elif recharge_water_litres <= 0:
        recharge_criterion = FeasibilityCriterion(
            criterion="recharge_water_quantity",
            result=CriterionStatus.FAILED,
            observed_value=recharge_water_litres,
            required_condition="A positive quantity of surplus rooftop runoff.",
            reason="The storage water balance has no surplus overflow to route to recharge.",
            source_ids=("CGWB_MANUAL_AR_2007",),
        )
    else:
        recharge_criterion = FeasibilityCriterion(
            criterion="recharge_water_quantity",
            result=CriterionStatus.PASSED,
            observed_value=recharge_water_litres,
            required_condition="A positive quantity of surplus rooftop runoff.",
            reason="The storage water balance reports positive overflow available for routing.",
            source_ids=("CGWB_MANUAL_AR_2007", "IRICEN_RWH_2022"),
        )

    post_monsoon = _is_post_monsoon(groundwater_observation_season)
    if not groundwater_has_observation_metadata or groundwater_depth_m_bgl is None:
        groundwater_criterion = FeasibilityCriterion(
            criterion="groundwater_observation",
            result=CriterionStatus.INSUFFICIENT_DATA,
            observed_value=groundwater_depth_m_bgl,
            required_condition=(
                "A dated, seasonal depth-to-water observation with spatial context."
            ),
            reason=groundwater_reason
            or "The groundwater depth lacks observation date, season or spatial context.",
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_NAQUIM"),
        )
    elif post_monsoon and groundwater_depth_m_bgl < 3:
        groundwater_criterion = FeasibilityCriterion(
            criterion="groundwater_observation",
            result=CriterionStatus.FAILED,
            observed_value=groundwater_depth_m_bgl,
            required_condition=(
                "Post-monsoon groundwater level must not be shallower than 3 m bgl."
            ),
            reason=(
                "CGWB states artificial recharge structures are not recommended where "
                "post-monsoon water levels are shallower than 3 m bgl."
            ),
            source_ids=("CGWB_AR_FAQ_2025",),
        )
    elif not post_monsoon:
        groundwater_criterion = FeasibilityCriterion(
            criterion="groundwater_observation",
            result=CriterionStatus.REQUIRES_VERIFICATION,
            observed_value=groundwater_depth_m_bgl,
            required_condition="A post-monsoon depth-to-water observation for the exclusion check.",
            reason=(
                "A groundwater observation exists, but it is not identified as post-monsoon."
            ),
            source_ids=("CGWB_AR_FAQ_2025", "CGWB_NAQUIM"),
        )
    else:
        groundwater_criterion = FeasibilityCriterion(
            criterion="groundwater_observation",
            result=CriterionStatus.PASSED,
            observed_value=groundwater_depth_m_bgl,
            required_condition=(
                "Post-monsoon groundwater level must not be shallower than 3 m bgl."
            ),
            reason=groundwater_reason or "A dated post-monsoon observation is available.",
            source_ids=("CGWB_AR_FAQ_2025", "CGWB_NAQUIM"),
        )

    if infiltration_is_property_measured and has_infiltration_evidence:
        infiltration_criterion = FeasibilityCriterion(
            criterion="infiltration_or_permeability",
            result=CriterionStatus.PASSED,
            observed_value="PROPERTY_MEASURED",
            required_condition="Site infiltration/permeability must be verified before final design.",
            reason="A property-level infiltration/percolation measurement is available.",
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_GUIDE_AR"),
        )
    elif has_infiltration_evidence:
        infiltration_criterion = FeasibilityCriterion(
            criterion="infiltration_or_permeability",
            result=CriterionStatus.REQUIRES_VERIFICATION,
            observed_value="REGIONAL_PROXY",
            required_condition="Property-level infiltration/permeability verification.",
            reason=infiltration_reason
            or "Regional soil evidence is only a proxy; a field test is required.",
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_GUIDE_AR"),
        )
    else:
        infiltration_criterion = FeasibilityCriterion(
            criterion="infiltration_or_permeability",
            result=CriterionStatus.REQUIRES_VERIFICATION,
            observed_value=None,
            required_condition="Property-level infiltration/permeability verification.",
            reason=infiltration_reason
            or "No measured infiltration/permeability result is available; a field test is required.",
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_GUIDE_AR"),
        )

    hydrogeology_criterion = FeasibilityCriterion(
        criterion="hydrogeology_and_aquifer",
        result=(
            CriterionStatus.PASSED
            if has_hydrogeology_evidence
            else CriterionStatus.INSUFFICIENT_DATA
        ),
        observed_value=None,
        required_condition=(
            "Applicable geology, geomorphology and aquifer characteristics at stated resolution."
        ),
        reason=hydrogeology_reason
        or (
            "Hydrogeological evidence is available."
            if has_hydrogeology_evidence
            else "No reviewed coordinate-level hydrogeological feature is available."
        ),
        source_ids=("CGWB_MANUAL_AR_2007", "CGWB_NAQUIM", "BHUVAN_OGC_GUIDANCE"),
    )

    quality_results = {
        WaterQualityStatus.VERIFIED_ACCEPTABLE: (
            CriterionStatus.PASSED,
            "Water-quality evidence is recorded as acceptable for recharge review.",
        ),
        WaterQualityStatus.NOT_VERIFIED: (
            CriterionStatus.REQUIRES_VERIFICATION,
            "Water quality and contamination risks require verification before construction.",
        ),
        WaterQualityStatus.UNSUITABLE: (
            CriterionStatus.FAILED,
            "The supplied water-quality review identifies the water as unsuitable for recharge.",
        ),
    }
    quality_result, quality_reason = quality_results[water_quality_status]
    quality_criterion = FeasibilityCriterion(
        criterion="water_quality_and_contamination_risk",
        result=quality_result,
        observed_value=water_quality_status.value,
        required_condition="Source-water quality and contamination risks must be acceptable.",
        reason=quality_reason,
        source_ids=("CGWB_MANUAL_AR_2007", "CGWB_AR_FAQ_2025"),
    )

    area_criterion = FeasibilityCriterion(
        criterion="available_site_area",
        result=(
            CriterionStatus.PASSED
            if available_ground_area_m2 > 0
            else CriterionStatus.FAILED
        ),
        observed_value=available_ground_area_m2,
        required_condition="Positive open ground area; final footprint checked during sizing.",
        reason=(
            "A positive construction footprint is available for structure-specific checking."
            if available_ground_area_m2 > 0
            else "No open ground area is available for a recharge structure."
        ),
        source_ids=("CGWB_MANUAL_AR_2007",),
    )

    criteria = (
        recharge_criterion,
        groundwater_criterion,
        infiltration_criterion,
        hydrogeology_criterion,
        quality_criterion,
        area_criterion,
    )
    failed = tuple(item.reason for item in criteria if item.result is CriterionStatus.FAILED)
    missing = tuple(
        item.reason for item in criteria if item.result is CriterionStatus.INSUFFICIENT_DATA
    )
    verification = tuple(
        item.reason
        for item in criteria
        if item.result is CriterionStatus.REQUIRES_VERIFICATION
    )
    passed = tuple(item.reason for item in criteria if item.result is CriterionStatus.PASSED)

    if failed:
        status = FeasibilityStatus.NOT_ELIGIBLE
    elif missing:
        status = FeasibilityStatus.INSUFFICIENT_DATA
    elif verification:
        status = FeasibilityStatus.CONDITIONALLY_ELIGIBLE
    else:
        status = FeasibilityStatus.ELIGIBLE

    return FeasibilityResult(
        status=status,
        criteria=criteria,
        reasons=(*failed, *missing, *verification),
        conditions_passed=passed,
        conditions_failed=failed,
        conditions_requiring_verification=verification,
        missing_data=missing,
        field_tests_recommended=tuple(
            reason
            for reason in verification
            if "infiltration" in reason.casefold() or "post-monsoon" in reason.casefold()
        ),
        source_ids=(
            "CGWB_MANUAL_AR_2007",
            "CGWB_GUIDE_AR",
            "CGWB_AR_FAQ_2025",
            "CGWB_NAQUIM",
            "BHUVAN_OGC_GUIDANCE",
            "IRICEN_RWH_2022",
        ),
    )
