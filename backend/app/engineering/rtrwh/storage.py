from dataclasses import dataclass
from enum import Enum

from ...domain.units import AreaSquareMeters, RainfallMM, RunoffCoefficient, VolumeLitres

METHOD_ID = "IRICEN_2022_MONTHLY_CUMULATIVE_SURPLUS"
DESIGN_MONTH_ORDER = (7, 8, 9, 10, 11, 12, 1, 2, 3, 4, 5, 6)
SOURCE_IDS = (
    "IRICEN_RWH_2022",
    "IMD_DISTRICT_MONTHLY_NORMALS_1971_2020",
    "CGWB_MANUAL_AR_2007",
)


class StorageSizingStatus(str, Enum):
    SIZE_AVAILABLE = "SIZE_AVAILABLE"
    NO_HARVESTABLE_WATER = "NO_HARVESTABLE_WATER"
    NO_POSITIVE_STORAGE_SURPLUS = "NO_POSITIVE_STORAGE_SURPLUS"
    INSUFFICIENT_DATA_FOR_SIZING = "INSUFFICIENT_DATA_FOR_SIZING"


@dataclass(frozen=True)
class StoragePeriodResult:
    month: int
    rainfall_mm: float
    inflow_litres: float
    demand_litres: float
    cumulative_surplus_litres: float
    supplied_litres: float
    unmet_demand_litres: float
    overflow_litres: float
    storage_end_litres: float


@dataclass(frozen=True)
class StorageSimulationResult:
    periods: tuple[StoragePeriodResult, ...]
    total_inflow_litres: float
    total_demand_litres: float
    total_supplied_litres: float
    total_unmet_demand_litres: float
    total_overflow_litres: float
    demand_met_percent: float
    depletion_months: tuple[int, ...]


@dataclass(frozen=True)
class StorageSizingResult:
    status: StorageSizingStatus
    recommended_litres: float | None
    method_id: str
    design_period: str
    rainfall_resolution: str | None
    demand_used_litres_per_month: float | None
    estimated_supply_litres: float | None
    estimated_overflow_litres: float | None
    demand_met_percent: float | None
    depletion_months: tuple[int, ...]
    periods: tuple[StoragePeriodResult, ...]
    assumptions: tuple[str, ...]
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    message: str


def _validate_monthly_rainfall(monthly_rainfall_mm: tuple[float, ...]) -> None:
    if len(monthly_rainfall_mm) != 12:
        raise ValueError("Exactly twelve monthly rainfall values are required.")
    for value in monthly_rainfall_mm:
        RainfallMM(value)


def simulate_storage(
    *,
    monthly_rainfall_mm: tuple[float, ...],
    roof_area: AreaSquareMeters,
    runoff_coefficient: RunoffCoefficient,
    monthly_demand: VolumeLitres,
    tank_capacity: VolumeLitres,
) -> StorageSimulationResult:
    """Simulate a finite tank for the IRICEN July-to-June design sequence."""

    _validate_monthly_rainfall(monthly_rainfall_mm)
    if monthly_demand.value <= 0:
        raise ValueError("Monthly rainwater demand must be greater than zero.")

    storage = 0.0
    cumulative_surplus = 0.0
    periods: list[StoragePeriodResult] = []
    for month in DESIGN_MONTH_ORDER:
        rainfall = monthly_rainfall_mm[month - 1]
        inflow = rainfall * roof_area.value * runoff_coefficient.value
        cumulative_surplus += inflow - monthly_demand.value
        available = storage + inflow
        supplied = min(monthly_demand.value, available)
        unmet = monthly_demand.value - supplied
        remaining = available - supplied
        overflow = max(0.0, remaining - tank_capacity.value)
        storage = min(remaining, tank_capacity.value)
        periods.append(
            StoragePeriodResult(
                month=month,
                rainfall_mm=rainfall,
                inflow_litres=round(inflow, 2),
                demand_litres=monthly_demand.value,
                cumulative_surplus_litres=round(cumulative_surplus, 2),
                supplied_litres=round(supplied, 2),
                unmet_demand_litres=round(unmet, 2),
                overflow_litres=round(overflow, 2),
                storage_end_litres=round(storage, 2),
            )
        )

    total_inflow = sum(period.inflow_litres for period in periods)
    total_demand = monthly_demand.value * 12
    total_supplied = sum(period.supplied_litres for period in periods)
    total_unmet = sum(period.unmet_demand_litres for period in periods)
    total_overflow = sum(period.overflow_litres for period in periods)
    return StorageSimulationResult(
        periods=tuple(periods),
        total_inflow_litres=round(total_inflow, 2),
        total_demand_litres=round(total_demand, 2),
        total_supplied_litres=round(total_supplied, 2),
        total_unmet_demand_litres=round(total_unmet, 2),
        total_overflow_litres=round(total_overflow, 2),
        demand_met_percent=round(total_supplied / total_demand * 100, 2),
        depletion_months=tuple(
            period.month for period in periods if period.unmet_demand_litres > 0
        ),
    )


def assess_storage_size(
    *,
    monthly_rainfall_mm: tuple[float, ...] | None = None,
    roof_area: AreaSquareMeters | None = None,
    runoff_coefficient: RunoffCoefficient | None = None,
    monthly_demand: VolumeLitres | None = None,
) -> StorageSizingResult:
    """Apply IRICEN §2.2.8.1's monthly cumulative-surplus method.

    IRICEN's published example orders the design year July through June and selects
    the maximum cumulative difference between harvested rainfall and demand. The
    accompanying finite-tank simulation reports normal-year performance; it is not
    a probabilistic reliability claim.
    """

    missing_inputs: list[str] = []
    if monthly_rainfall_mm is None:
        missing_inputs.append("twelve official monthly rainfall normals")
    if roof_area is None:
        missing_inputs.append("roof catchment area")
    if runoff_coefficient is None:
        missing_inputs.append("source-backed runoff coefficient")
    if monthly_demand is None:
        missing_inputs.append("planned monthly rainwater demand")
    if missing_inputs:
        return StorageSizingResult(
            status=StorageSizingStatus.INSUFFICIENT_DATA_FOR_SIZING,
            recommended_litres=None,
            method_id=METHOD_ID,
            design_period="July-June normal year",
            rainfall_resolution=(
                "monthly district normal" if monthly_rainfall_mm is not None else None
            ),
            demand_used_litres_per_month=(monthly_demand.value if monthly_demand else None),
            estimated_supply_litres=None,
            estimated_overflow_litres=None,
            demand_met_percent=None,
            depletion_months=(),
            periods=(),
            assumptions=(),
            missing_inputs=tuple(missing_inputs),
            source_ids=SOURCE_IDS,
            message=(
                "Tank capacity requires twelve official monthly rainfall normals, a "
                "source-backed catchment yield, and the user's planned monthly rainwater demand."
            ),
        )

    _validate_monthly_rainfall(monthly_rainfall_mm)
    if monthly_demand.value <= 0:
        raise ValueError("Monthly rainwater demand must be greater than zero.")

    ordered_inflows = [
        monthly_rainfall_mm[month - 1]
        * roof_area.value
        * runoff_coefficient.value
        for month in DESIGN_MONTH_ORDER
    ]
    if sum(ordered_inflows) <= 0:
        return StorageSizingResult(
            status=StorageSizingStatus.NO_HARVESTABLE_WATER,
            recommended_litres=None,
            method_id=METHOD_ID,
            design_period="July-June normal year",
            rainfall_resolution="monthly district normal",
            demand_used_litres_per_month=monthly_demand.value,
            estimated_supply_litres=0,
            estimated_overflow_litres=0,
            demand_met_percent=0,
            depletion_months=DESIGN_MONTH_ORDER,
            periods=(),
            assumptions=(),
            missing_inputs=(),
            source_ids=SOURCE_IDS,
            message="The monthly rainfall series yields no harvestable water for storage.",
        )

    cumulative_surplus = 0.0
    maximum_surplus = 0.0
    for inflow in ordered_inflows:
        cumulative_surplus += inflow - monthly_demand.value
        maximum_surplus = max(maximum_surplus, cumulative_surplus)
    if maximum_surplus <= 0:
        return StorageSizingResult(
            status=StorageSizingStatus.NO_POSITIVE_STORAGE_SURPLUS,
            recommended_litres=None,
            method_id=METHOD_ID,
            design_period="July-June normal year",
            rainfall_resolution="IMD district monthly normal, 1971-2020",
            demand_used_litres_per_month=monthly_demand.value,
            estimated_supply_litres=None,
            estimated_overflow_litres=None,
            demand_met_percent=None,
            depletion_months=(),
            periods=(),
            assumptions=(
                "Monthly demand is constant at the user-entered value.",
                "The design sequence follows IRICEN's July-to-June worked method.",
            ),
            missing_inputs=(),
            source_ids=SOURCE_IDS,
            message=(
                "The monthly series has no positive cumulative harvest surplus, so "
                "the IRICEN method does not produce a positive tank capacity."
            ),
        )
    recommended_capacity = VolumeLitres(round(maximum_surplus, 2))
    simulation = simulate_storage(
        monthly_rainfall_mm=monthly_rainfall_mm,
        roof_area=roof_area,
        runoff_coefficient=runoff_coefficient,
        monthly_demand=monthly_demand,
        tank_capacity=recommended_capacity,
    )
    return StorageSizingResult(
        status=StorageSizingStatus.SIZE_AVAILABLE,
        recommended_litres=recommended_capacity.value,
        method_id=METHOD_ID,
        design_period="July-June normal year",
        rainfall_resolution="IMD district monthly normal, 1971-2020",
        demand_used_litres_per_month=monthly_demand.value,
        estimated_supply_litres=simulation.total_supplied_litres,
        estimated_overflow_litres=simulation.total_overflow_litres,
        demand_met_percent=simulation.demand_met_percent,
        depletion_months=simulation.depletion_months,
        periods=simulation.periods,
        assumptions=(
            "Monthly demand is constant at the user-entered value.",
            "The design sequence follows IRICEN's July-to-June worked method.",
            "The tank starts empty; monthly inflow is available before that month's demand.",
            "Performance uses climatological monthly normals and is not real-year reliability.",
        ),
        missing_inputs=(),
        source_ids=SOURCE_IDS,
        message=(
            "Capacity is the maximum cumulative monthly surplus using the published "
            "IRICEN method; performance metrics describe a normal year, not guaranteed reliability."
        ),
    )
