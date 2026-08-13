from dataclasses import dataclass


@dataclass(frozen=True)
class RechargeQuantityResult:
    status: str
    potential_recharge_litres_per_year: float | None
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    message: str


def assess_recharge_quantity() -> RechargeQuantityResult:
    return RechargeQuantityResult(
        status="INSUFFICIENT_DATA",
        potential_recharge_litres_per_year=None,
        missing_inputs=(
            "water allocated to storage or direct use",
            "documented additional losses not represented by the runoff coefficient",
            "overflow and other allocations",
            "site/aquifer acceptance capacity",
        ),
        source_ids=("CGWB_MANUAL_AR_2007", "CGWB_MASTER_PLAN_AR_2020"),
        message=(
            "Rechargeable water cannot be derived from rooftop harvest alone; a documented "
            "allocation balance and site/aquifer acceptance evidence are required."
        ),
    )
