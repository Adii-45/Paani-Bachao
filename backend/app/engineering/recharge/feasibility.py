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
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    DATA_AVAILABLE = "DATA_AVAILABLE"


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
    source_ids: tuple[str, ...]


def evaluate_feasibility(
    *,
    groundwater_depth_m_bgl: float,
    groundwater_has_observation_metadata: bool,
    has_recharge_water_balance: bool,
    has_infiltration_evidence: bool,
    has_hydrogeology_evidence: bool,
    has_water_quality_review: bool,
    available_ground_area_m2: float,
) -> FeasibilityResult:
    """Evaluate evidence sufficiency without inventing physical thresholds."""

    criteria = (
        FeasibilityCriterion(
            criterion="recharge_water_quantity",
            result=(
                CriterionStatus.DATA_AVAILABLE
                if has_recharge_water_balance
                else CriterionStatus.INSUFFICIENT_DATA
            ),
            observed_value=None,
            required_condition="A documented water balance after storage/use and losses.",
            reason=(
                "A recharge-water balance is available."
                if has_recharge_water_balance
                else "Storage, use, overflow and other allocation data are not available."
            ),
            source_ids=("CGWB_MANUAL_AR_2007",),
        ),
        FeasibilityCriterion(
            criterion="groundwater_observation",
            result=(
                CriterionStatus.DATA_AVAILABLE
                if groundwater_has_observation_metadata
                else CriterionStatus.INSUFFICIENT_DATA
            ),
            observed_value=groundwater_depth_m_bgl,
            required_condition=(
                "A time-stamped groundwater depth observation with method, season and "
                "spatial uncertainty."
            ),
            reason=(
                "Groundwater observation metadata are available."
                if groundwater_has_observation_metadata
                else "The supplied depth has no observation date, season, method or uncertainty."
            ),
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_NAQUIM"),
        ),
        FeasibilityCriterion(
            criterion="infiltration_or_permeability",
            result=(
                CriterionStatus.DATA_AVAILABLE
                if has_infiltration_evidence
                else CriterionStatus.INSUFFICIENT_DATA
            ),
            observed_value=None,
            required_condition="Measured or authoritative infiltration/permeability evidence.",
            reason=(
                "Infiltration evidence is available."
                if has_infiltration_evidence
                else "A broad homeowner soil label is not an infiltration measurement."
            ),
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_GUIDE_AR"),
        ),
        FeasibilityCriterion(
            criterion="hydrogeology_and_aquifer",
            result=(
                CriterionStatus.DATA_AVAILABLE
                if has_hydrogeology_evidence
                else CriterionStatus.INSUFFICIENT_DATA
            ),
            observed_value=None,
            required_condition=(
                "Applicable geology, geomorphology and aquifer characteristics at stated resolution."
            ),
            reason=(
                "Hydrogeological evidence is available."
                if has_hydrogeology_evidence
                else "No applicable CGWB/NAQUIM or documented geospatial feature is available."
            ),
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_NAQUIM", "BHUVAN_OGC_GUIDANCE"),
        ),
        FeasibilityCriterion(
            criterion="water_quality_and_contamination_risk",
            result=(
                CriterionStatus.DATA_AVAILABLE
                if has_water_quality_review
                else CriterionStatus.INSUFFICIENT_DATA
            ),
            observed_value=None,
            required_condition="Source-water and groundwater-quality/contamination review.",
            reason=(
                "Water-quality evidence is available."
                if has_water_quality_review
                else "Water quality and contamination risks have not been assessed."
            ),
            source_ids=("CGWB_MANUAL_AR_2007", "CGWB_NAQUIM"),
        ),
        FeasibilityCriterion(
            criterion="available_site_area",
            result=CriterionStatus.DATA_AVAILABLE,
            observed_value=available_ground_area_m2,
            required_condition=(
                "User-supplied footprint to be checked against a technically applicable structure."
            ),
            reason=(
                "Area is recorded, but adequacy cannot be judged before structure selection and design."
            ),
            source_ids=("CGWB_MANUAL_AR_2007",),
        ),
    )
    missing = tuple(
        criterion.reason
        for criterion in criteria
        if criterion.result is CriterionStatus.INSUFFICIENT_DATA
    )
    return FeasibilityResult(
        status=FeasibilityStatus.INSUFFICIENT_DATA,
        criteria=criteria,
        reasons=missing,
        source_ids=(
            "CGWB_MANUAL_AR_2007",
            "CGWB_GUIDE_AR",
            "CGWB_NAQUIM",
            "BHUVAN_OGC_GUIDANCE",
        ),
    )
