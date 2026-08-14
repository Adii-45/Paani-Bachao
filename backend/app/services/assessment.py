from collections.abc import Iterable

from ..domain.environment import LocationQuery
from ..domain.environment import RainfallLookup
from ..domain.location import LocationResolutionStatus
from ..domain.units import AreaSquareMeters, RainfallMM, RunoffCoefficient
from ..engineering.recharge import (
    assess_recharge_quantity,
    assess_structure_size,
    evaluate_feasibility,
    select_structure,
)
from ..engineering.rtrwh import assess_storage_size, calculate_annual_harvest
from ..provenance.models import DataQuality, DataStatus, ValueProvenance
from ..provenance.registry import citations_for
from ..providers.rainfall import NormalizedImdRainfallProvider
from ..providers.location import LocationResolver, NominatimLocationResolver
from ..providers.rainfall.base import RainfallProvider
from ..providers.runoff import SourceBackedRunoffCoefficientProvider
from ..schemas import (
    ArtificialRechargeResult,
    AssessmentRequest,
    AssessmentResponse,
    DerivedData,
    FeasibilityCriterionResponse,
    FormulaDetails,
    NormalizedLocationEvidence,
    RainfallEvidence,
    RtrwhResult,
    RunoffCoefficientEvidence,
)


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def create_assessment(
    inputs: AssessmentRequest,
    *,
    location_resolver: LocationResolver | None = None,
    rainfall_provider: RainfallProvider | None = None,
) -> AssessmentResponse:
    location_query = LocationQuery(
        location=inputs.location,
        latitude=inputs.latitude,
        longitude=inputs.longitude,
        state=inputs.state,
        district=inputs.district,
    )
    location_resolution = (location_resolver or NominatimLocationResolver()).resolve(
        location_query
    )
    normalized_location = location_resolution.location
    if (
        location_resolution.status is LocationResolutionStatus.RESOLVED
        and normalized_location is not None
    ):
        rainfall_lookup = (rainfall_provider or NormalizedImdRainfallProvider()).lookup(
            normalized_location
        )
    else:
        rainfall_lookup = RainfallLookup(
            status=DataStatus.DATA_UNAVAILABLE,
            error_code="LOCATION_NOT_RESOLVED",
            message=(
                "RainfallDataUnavailable: rainfall lookup was not attempted because "
                f"the location was not resolved. {location_resolution.message}"
            ),
        )
    coefficient_lookup = SourceBackedRunoffCoefficientProvider().lookup(
        inputs.roofMaterial.value
    )

    rainfall_record = rainfall_lookup.record
    coefficient_record = coefficient_lookup.record
    rainfall_value = rainfall_record.rainfall_mm if rainfall_record else None
    coefficient_value = (
        coefficient_record.value_range.selected_value if coefficient_record else None
    )

    rainfall_provenance = None
    if rainfall_record:
        rainfall_provenance = ValueProvenance(
            quality=DataQuality.AUTHORITATIVE_DATASET,
            source_ids=[rainfall_record.source_id],
            source_record=rainfall_record.source_record,
            source_date_or_version=rainfall_record.dataset_version,
            spatial_resolution=rainfall_record.spatial_resolution,
            temporal_resolution=rainfall_record.statistic_type,
            retrieved_at=rainfall_record.retrieved_at,
        )

    rainfall_evidence = RainfallEvidence(
        status=rainfall_lookup.status,
        value=rainfall_value,
        statisticType=rainfall_record.statistic_type if rainfall_record else None,
        referencePeriod=rainfall_record.reference_period if rainfall_record else None,
        spatialResolution=rainfall_record.spatial_resolution if rainfall_record else None,
        sourceRecord=rainfall_record.source_record if rainfall_record else None,
        datasetVersion=rainfall_record.dataset_version if rainfall_record else None,
        sourceName=rainfall_record.source_name if rainfall_record else None,
        sourceUrl=rainfall_record.source_url if rainfall_record else None,
        provenance=rainfall_provenance,
        message=rainfall_lookup.message,
        errorCode=rainfall_lookup.error_code,
    )
    coefficient_evidence = RunoffCoefficientEvidence(
        status=coefficient_lookup.status,
        valueRange=coefficient_record.value_range if coefficient_record else None,
        condition=coefficient_record.condition if coefficient_record else None,
        provenance=coefficient_record.provenance if coefficient_record else None,
        message=coefficient_lookup.message,
    )

    harvest = None
    usable_rainfall = rainfall_lookup.status in {
        DataStatus.DATA_AVAILABLE,
        DataStatus.DATA_STALE,
    }
    if usable_rainfall and rainfall_value is not None and coefficient_value is not None:
        harvest = calculate_annual_harvest(
            RainfallMM(rainfall_value),
            AreaSquareMeters(inputs.roofAreaM2),
            RunoffCoefficient(coefficient_value),
        )

    storage = assess_storage_size()
    recharge_quantity = assess_recharge_quantity()
    groundwater_has_metadata = all(
        (
            inputs.groundwaterObservationDate,
            inputs.groundwaterObservationSeason,
            inputs.groundwaterObservationMethod,
            inputs.groundwaterSource,
        )
    )
    feasibility = evaluate_feasibility(
        groundwater_depth_m_bgl=inputs.groundwaterDepthM,
        groundwater_has_observation_metadata=groundwater_has_metadata,
        has_recharge_water_balance=False,
        has_infiltration_evidence=False,
        has_hydrogeology_evidence=False,
        has_water_quality_review=False,
        available_ground_area_m2=inputs.availableGroundAreaM2,
    )
    structure_selection = select_structure(feasibility)
    structure_sizing = assess_structure_size(structure_selection)

    warnings: list[str] = []
    if rainfall_lookup.status is DataStatus.DATA_STALE:
        warnings.append(rainfall_lookup.message)
    elif rainfall_lookup.status is not DataStatus.DATA_AVAILABLE:
        warnings.append(rainfall_lookup.message)
    if coefficient_lookup.status is not DataStatus.DATA_AVAILABLE:
        warnings.append(coefficient_lookup.message)
    warnings.extend(
        [
            storage.message,
            recharge_quantity.message,
            "Artificial recharge feasibility is incomplete because mandatory site evidence is missing.",
            structure_sizing.message,
        ]
    )

    source_ids = _unique(
        [
            "CGWB_MANUAL_AR_2007",
            "BIS_IS_15797_2008",
            *feasibility.source_ids,
            *recharge_quantity.source_ids,
            *structure_selection.source_ids,
            *structure_sizing.source_ids,
            *(
                ["OPENSTREETMAP_NOMINATIM"]
                if normalized_location
                and normalized_location.provider == "OpenStreetMap Nominatim"
                else []
            ),
            *(rainfall_record.source_id for _ in [0] if rainfall_record),
            *(coefficient_record.source_ids if coefficient_record else []),
        ]
    )
    formula_assumptions = [
        "Mean annual/normal rainfall represents an average year, not a design storm.",
        "The runoff coefficient represents collection losses covered by its cited source and conditions.",
    ]

    return AssessmentResponse(
        inputs=inputs,
        derived=DerivedData(
            locationStatus=location_resolution.status,
            normalizedLocation=(
                NormalizedLocationEvidence(
                    input=normalized_location.input,
                    canonicalName=normalized_location.canonical_name,
                    latitude=normalized_location.latitude,
                    longitude=normalized_location.longitude,
                    district=normalized_location.district,
                    state=normalized_location.state,
                    country=normalized_location.country,
                    provider=normalized_location.provider,
                    providerPlaceId=normalized_location.provider_place_id,
                    confidence=normalized_location.confidence,
                    candidateCount=normalized_location.candidate_count,
                    message=location_resolution.message,
                )
                if normalized_location
                else None
            ),
            annualRainfallMm=rainfall_value,
            rainfallSource=(
                f"{rainfall_record.source_name}: {rainfall_record.dataset_version}"
                if rainfall_record
                else None
            ),
            runoffCoefficient=coefficient_value,
            rainfallStatus=rainfall_lookup.status,
            rainfall=rainfall_evidence,
            runoffCoefficientStatus=coefficient_lookup.status,
            runoffCoefficientEvidence=coefficient_evidence,
        ),
        rtrwh=RtrwhResult(
            potentialLitresPerYear=(
                harvest.harvestable_volume.value if harvest else None
            ),
            recommendedSizeLitres=storage.recommended_litres,
            sizingMessage=storage.message,
            calculationStatus=(
                DataStatus.DATA_AVAILABLE if harvest else DataStatus.INSUFFICIENT_DATA
            ),
            sizingStatus=storage.status.value,
            sizingMethodId=storage.method_id,
            sizingMissingInputs=list(storage.missing_inputs),
            sizingSourceIds=list(storage.source_ids),
        ),
        artificialRecharge=ArtificialRechargeResult(
            potential=None,
            potentialRechargeLitresPerYear=(
                recharge_quantity.potential_recharge_litres_per_year
            ),
            recommendedStructure=None,
            dimensions=structure_sizing.dimensions,
            message=recharge_quantity.message,
            feasibilityStatus=feasibility.status.value,
            criteria=[
                FeasibilityCriterionResponse(
                    criterion=criterion.criterion,
                    result=criterion.result.value,
                    observedValue=criterion.observed_value,
                    requiredCondition=criterion.required_condition,
                    reason=criterion.reason,
                    sourceIds=list(criterion.source_ids),
                )
                for criterion in feasibility.criteria
            ],
            reasons=list(feasibility.reasons),
            quantityStatus=recharge_quantity.status,
            quantityMissingInputs=list(recharge_quantity.missing_inputs),
            structureSelectionStatus=structure_selection.status,
            alternativeStructures=list(structure_selection.alternative_structures),
            selectionReasons=list(structure_selection.selection_reasons),
            rejectedStructures=[],
            structureMissingInputs=list(structure_selection.missing_inputs),
            sizingStatus=structure_sizing.status,
            sizingMissingInputs=list(structure_sizing.missing_inputs),
            sourceIds=_unique(
                [
                    *feasibility.source_ids,
                    *recharge_quantity.source_ids,
                    *structure_selection.source_ids,
                    *structure_sizing.source_ids,
                ]
            ),
        ),
        rtrwhSuitability="SUITABILITY_NOT_DETERMINED",
        dataCompleteness="INSUFFICIENT",
        ruleset="SOURCE_BACKED",
        isDemoData=False,
        formula=FormulaDetails(
            expression="rainfall (mm/year) × roof area (m²) × runoff coefficient",
            roofAreaM2=inputs.roofAreaM2,
            annualRainfallMm=rainfall_value,
            runoffCoefficient=coefficient_value,
            methodId=(
                harvest.method_id
                if harvest
                else "CGWB_MANUAL_2007_RTRWH_ANNUAL_VOLUME"
            ),
            grossRainfallVolumeLitres=(
                harvest.gross_rainfall_volume.value if harvest else None
            ),
            estimatedLossesLitres=(harvest.estimated_losses.value if harvest else None),
            harvestableVolumeLitres=(
                harvest.harvestable_volume.value if harvest else None
            ),
            sourceIds=["CGWB_MANUAL_AR_2007"],
            assumptions=formula_assumptions,
        ),
        warnings=_unique(warnings),
        sources=citations_for(*source_ids),
    )
