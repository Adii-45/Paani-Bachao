from ..calculations.recharge import classify_recharge, select_structure
from ..calculations.rtrwh import calculate_potential_litres
from ..calculations.sizing import recommended_storage_litres
from ..rules.loader import active_ruleset, load_rule
from ..schemas import (
    ArtificialRechargeResult,
    AssessmentRequest,
    AssessmentResponse,
    DerivedData,
    FormulaDetails,
    RtrwhResult,
)
from .rainfall import get_rainfall

DEMO_WARNING = "DEMO / DEVELOPMENT VALUE — NOT VALIDATED"


def create_assessment(inputs: AssessmentRequest) -> AssessmentResponse:
    ruleset = active_ruleset()
    rainfall = get_rainfall(inputs.location, load_rule("rainfall", ruleset))
    runoff_config = load_rule("runoff_coefficients", ruleset)
    coefficient = runoff_config.get("materials", {}).get(inputs.roofMaterial.value)
    annual_rainfall = rainfall.get("annualRainfallMm") if rainfall else None
    runoff = coefficient.get("runoffCoefficient") if coefficient else None

    potential = None
    if annual_rainfall is not None and runoff is not None:
        potential = calculate_potential_litres(inputs.roofAreaM2, annual_rainfall, runoff)

    size, sizing_message = (None, "Assessment unavailable. Engineering sizing rule not configured yet.")
    if potential is not None:
        size, sizing_message = recommended_storage_litres(
            potential, load_rule("rtrwh_sizing", ruleset)
        )

    classification, recharge_fraction = classify_recharge(
        inputs.soilType.value,
        inputs.groundwaterDepthM,
        inputs.availableGroundAreaM2,
        load_rule("recharge_rules", ruleset),
    )
    recharge_litres = (
        round(potential * recharge_fraction, 2)
        if potential is not None and recharge_fraction is not None
        else None
    )
    structure, dimensions = select_structure(
        classification,
        inputs.availableGroundAreaM2,
        load_rule("ar_structures", ruleset),
    )

    unknowns = sum(
        [inputs.roofMaterial.value == "DONT_KNOW", inputs.soilType.value == "DONT_KNOW"]
    )
    completeness = "GOOD" if unknowns == 0 else "LIMITED"
    if annual_rainfall is None or runoff is None:
        completeness = "INSUFFICIENT"

    warnings: list[str] = []
    if ruleset == "demo":
        warnings.append(DEMO_WARNING)
    if annual_rainfall is None:
        warnings.append("Rainfall data is not configured for this location.")
    if runoff is None:
        warnings.append("Runoff coefficient is not configured for this roof material.")
    if classification is None:
        warnings.append("Artificial recharge engineering rule not configured for this combination.")
    if structure is None:
        warnings.append("Artificial recharge structure or sizing rule not configured for this combination.")

    recharge_message = None
    if classification is None:
        recharge_message = "Assessment unavailable for this combination. Engineering rule not configured yet."
    elif structure is None:
        recharge_message = "Recharge potential is available, but a structure rule is not configured."

    return AssessmentResponse(
        inputs=inputs,
        derived=DerivedData(
            annualRainfallMm=annual_rainfall,
            rainfallSource=rainfall.get("source") if rainfall else None,
            runoffCoefficient=runoff,
        ),
        rtrwh=RtrwhResult(
            potentialLitresPerYear=potential,
            recommendedSizeLitres=size,
            sizingMessage=sizing_message,
        ),
        artificialRecharge=ArtificialRechargeResult(
            potential=classification,
            potentialRechargeLitresPerYear=recharge_litres,
            recommendedStructure=structure,
            dimensions=dimensions,
            message=recharge_message,
        ),
        rtrwhSuitability="SUITABLE" if potential is not None else "NOT ASSESSED",
        dataCompleteness=completeness,
        ruleset=ruleset.upper(),
        isDemoData=ruleset == "demo",
        formula=FormulaDetails(
            expression="roof area (m²) × rainfall (mm/year) × runoff coefficient",
            roofAreaM2=inputs.roofAreaM2,
            annualRainfallMm=annual_rainfall,
            runoffCoefficient=runoff,
        ),
        warnings=warnings,
    )
