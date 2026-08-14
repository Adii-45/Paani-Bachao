from dataclasses import dataclass

from ...domain.units import (
    AreaSquareMeters,
    RainfallMM,
    RunoffCoefficient,
    VolumeLitres,
)

METHOD_ID = "CGWB_MANUAL_2007_RTRWH_ANNUAL_VOLUME"
SOURCE_IDS = ["CGWB_MANUAL_AR_2007"]


@dataclass(frozen=True)
class HarvestingCalculation:
    rainfall: RainfallMM
    roof_area: AreaSquareMeters
    runoff_coefficient: RunoffCoefficient
    gross_rainfall_volume: VolumeLitres
    estimated_losses: VolumeLitres
    harvestable_volume: VolumeLitres
    method_id: str = METHOD_ID
    source_ids: tuple[str, ...] = tuple(SOURCE_IDS)


def calculate_annual_harvest(
    rainfall: RainfallMM,
    roof_area: AreaSquareMeters,
    runoff_coefficient: RunoffCoefficient,
) -> HarvestingCalculation:
    """Calculate CGWB annual rooftop water availability with explicit units.

    CGWB Manual (2007), §7.2.7.1 and §7.3.1, document page 119.
    The conversion follows from 1 mm = 0.001 m and 1 m³ = 1,000 L,
    therefore 1 mm over 1 m² equals 1 litre.
    """

    gross_litres = rainfall.value * roof_area.value
    harvestable_litres = gross_litres * runoff_coefficient.value
    loss_litres = gross_litres - harvestable_litres
    return HarvestingCalculation(
        rainfall=rainfall,
        roof_area=roof_area,
        runoff_coefficient=runoff_coefficient,
        gross_rainfall_volume=VolumeLitres(round(gross_litres, 2)),
        estimated_losses=VolumeLitres(round(loss_litres, 2)),
        harvestable_volume=VolumeLitres(round(harvestable_litres, 2)),
    )
