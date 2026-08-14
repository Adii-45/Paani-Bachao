from dataclasses import dataclass
from enum import Enum


METHOD_ID = "IRICEN_STORAGE_OVERFLOW_AVAILABLE_FOR_AR"
SOURCE_IDS = ("IRICEN_RWH_2022", "CGWB_MANUAL_AR_2007")


class RechargeQuantityStatus(str, Enum):
    DATA_AVAILABLE = "DATA_AVAILABLE"
    NO_RECHARGE_SURPLUS = "NO_RECHARGE_SURPLUS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class RechargeQuantityResult:
    status: RechargeQuantityStatus
    annual_harvest_litres: float | None
    annual_demand_supplied_litres: float | None
    annual_overflow_litres: float | None
    catchment_losses_litres: float | None
    ending_storage_litres: float | None
    potential_recharge_litres_per_year: float | None
    method_id: str
    assumptions: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    message: str


def assess_recharge_quantity(
    *,
    annual_harvest_litres: float | None = None,
    annual_demand_supplied_litres: float | None = None,
    annual_overflow_litres: float | None = None,
    catchment_losses_litres: float | None = None,
    ending_storage_litres: float | None = None,
) -> RechargeQuantityResult:
    """Expose simulated tank overflow as water potentially routable to AR.

    The input is the output of the finite-tank water balance.  This function does
    not estimate actual aquifer recharge: acceptance, water quality and site
    feasibility are evaluated separately.
    """

    values = {
        "annual harvest from the monthly storage simulation": annual_harvest_litres,
        "annual water supplied from storage": annual_demand_supplied_litres,
        "annual tank overflow": annual_overflow_litres,
        "ending tank storage": ending_storage_litres,
    }
    missing = tuple(name for name, value in values.items() if value is None)
    if missing:
        return RechargeQuantityResult(
            status=RechargeQuantityStatus.INSUFFICIENT_DATA,
            annual_harvest_litres=annual_harvest_litres,
            annual_demand_supplied_litres=annual_demand_supplied_litres,
            annual_overflow_litres=annual_overflow_litres,
            catchment_losses_litres=catchment_losses_litres,
            ending_storage_litres=ending_storage_litres,
            potential_recharge_litres_per_year=None,
            method_id=METHOD_ID,
            assumptions=(),
            missing_inputs=missing,
            source_ids=SOURCE_IDS,
            message=(
                "Recharge-available water requires a completed storage water balance; "
                "no fraction of annual rooftop harvest has been substituted."
            ),
        )

    numeric_values = [
        annual_harvest_litres,
        annual_demand_supplied_litres,
        annual_overflow_litres,
        ending_storage_litres,
    ]
    if catchment_losses_litres is not None:
        numeric_values.append(catchment_losses_litres)
    if any(value < 0 for value in numeric_values):
        raise ValueError("Recharge water-balance values cannot be negative.")

    accounted = (
        annual_demand_supplied_litres
        + annual_overflow_litres
        + ending_storage_litres
    )
    if abs(accounted - annual_harvest_litres) > 0.05:
        raise ValueError(
            "Storage water balance is not conserved: harvest must equal supplied "
            "water plus overflow plus ending storage."
        )
    if annual_overflow_litres > annual_harvest_litres:
        raise ValueError("Recharge-available overflow cannot exceed harvested water.")

    status = (
        RechargeQuantityStatus.DATA_AVAILABLE
        if annual_overflow_litres > 0
        else RechargeQuantityStatus.NO_RECHARGE_SURPLUS
    )
    return RechargeQuantityResult(
        status=status,
        annual_harvest_litres=round(annual_harvest_litres, 2),
        annual_demand_supplied_litres=round(annual_demand_supplied_litres, 2),
        annual_overflow_litres=round(annual_overflow_litres, 2),
        catchment_losses_litres=(
            round(catchment_losses_litres, 2)
            if catchment_losses_litres is not None
            else None
        ),
        ending_storage_litres=round(ending_storage_litres, 2),
        potential_recharge_litres_per_year=round(annual_overflow_litres, 2),
        method_id=METHOD_ID,
        assumptions=(
            "Only simulated tank overflow is counted as potentially available for recharge.",
            "Catchment losses are already represented by the cited roof runoff coefficient.",
            "The value is water available for routing, not a claim that the aquifer will accept it.",
        ),
        missing_inputs=(),
        source_ids=SOURCE_IDS,
        message=(
            "Potential recharge water is the annual overflow from the documented "
            "normal-year storage simulation."
            if annual_overflow_litres > 0
            else "The storage simulation produces no overflow available for recharge."
        ),
    )
