from app.schemas import AssessmentRequest
from app.services.assessment import DEMO_WARNING, create_assessment


def request(**overrides: object) -> AssessmentRequest:
    values: dict[str, object] = {
        "location": "Bengaluru",
        "roofAreaM2": 120,
        "roofMaterial": "RCC",
        "soilType": "SANDY_LOAM",
        "groundwaterDepthM": 8,
        "availableGroundAreaM2": 15,
    }
    values.update(overrides)
    return AssessmentRequest.model_validate(values)


def test_normal_suitable_property_reference_scenario() -> None:
    result = create_assessment(request())

    assert result.derived.annualRainfallMm == 970
    assert result.derived.runoffCoefficient == 0.8
    assert result.rtrwh.potentialLitresPerYear == 93_120
    assert result.rtrwh.recommendedSizeLitres == 6_000
    assert result.artificialRecharge.potential == "HIGH"
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 60_528
    assert result.artificialRecharge.recommendedStructure is not None
    assert result.artificialRecharge.recommendedStructure.type == "RECHARGE_TRENCH"
    assert result.artificialRecharge.dimensions == {
        "lengthM": 3,
        "widthM": 1,
        "depthM": 1.5,
    }
    assert result.rtrwhSuitability == "SUITABLE"
    assert result.dataCompleteness == "GOOD"
    assert result.assessmentStatus == "PRELIMINARY"
    assert result.warnings == [DEMO_WARNING]


def test_poor_recharge_conditions_reference_scenario() -> None:
    result = create_assessment(
        request(
            roofAreaM2=100,
            soilType="ROCKY",
            groundwaterDepthM=0,
            availableGroundAreaM2=0,
        )
    )

    assert result.artificialRecharge.potential == "NOT_RECOMMENDED"
    assert result.artificialRecharge.potentialRechargeLitresPerYear == 7_760
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
    assert "structure or sizing rule not configured" in result.warnings[-1]


def test_insufficient_ground_area_has_classification_but_no_structure() -> None:
    result = create_assessment(
        request(soilType="SANDY", groundwaterDepthM=8, availableGroundAreaM2=3.99)
    )

    assert result.artificialRecharge.potential == "MEDIUM"
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
    assert result.artificialRecharge.message == (
        "Recharge potential is available, but a structure rule is not configured."
    )


def test_unknown_soil_returns_limited_explicit_unavailable_recharge() -> None:
    result = create_assessment(request(soilType="DONT_KNOW"))

    assert result.rtrwh.potentialLitresPerYear == 93_120
    assert result.artificialRecharge.potential is None
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.artificialRecharge.recommendedStructure is None
    assert result.dataCompleteness == "LIMITED"
    assert "Engineering rule not configured yet" in result.artificialRecharge.message


def test_unconfigured_location_does_not_fabricate_rainfall_or_harvest() -> None:
    result = create_assessment(request(location="Atlantis"))

    assert result.derived.annualRainfallMm is None
    assert result.derived.rainfallSource is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.artificialRecharge.potentialRechargeLitresPerYear is None
    assert result.rtrwhSuitability == "NOT ASSESSED"
    assert result.dataCompleteness == "INSUFFICIENT"
    assert "Rainfall data is not configured for this location." in result.warnings


def test_unconfigured_roof_material_does_not_use_a_default_coefficient() -> None:
    result = create_assessment(request(roofMaterial="OTHER"))

    assert result.derived.runoffCoefficient is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.dataCompleteness == "INSUFFICIENT"
    assert "Runoff coefficient is not configured for this roof material." in result.warnings


def test_production_placeholders_return_unavailable_results_without_fabrication(
    monkeypatch,
) -> None:
    monkeypatch.setenv("RAINASSESS_RULESET", "production")
    result = create_assessment(request())

    assert result.ruleset == "PRODUCTION"
    assert result.isDemoData is False
    assert result.derived.annualRainfallMm is None
    assert result.derived.runoffCoefficient is None
    assert result.rtrwh.potentialLitresPerYear is None
    assert result.rtrwh.recommendedSizeLitres is None
    assert result.artificialRecharge.potential is None
    assert result.artificialRecharge.recommendedStructure is None
    assert result.artificialRecharge.dimensions is None
    assert result.dataCompleteness == "INSUFFICIENT"
    assert DEMO_WARNING not in result.warnings


def test_formula_transparency_matches_the_calculation_inputs() -> None:
    result = create_assessment(request(roofAreaM2=42.5, location="Chennai", roofMaterial="TILES"))

    assert result.rtrwh.potentialLitresPerYear == 44_625
    assert result.formula.model_dump() == {
        "expression": "roof area (m²) × rainfall (mm/year) × runoff coefficient",
        "roofAreaM2": 42.5,
        "annualRainfallMm": 1_400,
        "runoffCoefficient": 0.75,
    }
