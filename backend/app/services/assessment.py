from collections.abc import Iterable

from ..domain.environment import LocationQuery
from ..domain.units import AreaSquareMeters, RainfallMM, RunoffCoefficient, VolumeLitres
from ..engineering.recharge import (
    WaterQualityStatus,
    assess_recharge_quantity,
    assess_structure_size,
    evaluate_feasibility,
    select_structure,
)
from ..engineering.rtrwh import (
    StorageSizingStatus,
    assess_storage_size,
    calculate_annual_harvest,
    simulate_storage,
)
from ..provenance.models import DataQuality, DataStatus, ValueProvenance
from ..provenance.registry import citations_for
from ..providers.environmental import (
    GroundwaterProvider,
    HydrogeologyProvider,
    SoilProvider,
)
from ..providers.location import LocationResolver
from ..providers.rainfall.base import RainfallProvider
from ..providers.runoff import SourceBackedRunoffCoefficientProvider
from ..schemas import (
    ArtificialRechargeResult,
    AssessmentRequest,
    AssessmentResponse,
    DerivedData,
    EnvironmentalDataEvidence,
    EnvironmentalProviderEvidence,
    FeasibilityCriterionResponse,
    FormulaDetails,
    NormalizedLocationEvidence,
    RainfallEvidence,
    RejectedStructureResponse,
    RtrwhResult,
    RunoffCoefficientEvidence,
    StoragePeriodResponse,
    StructureRecommendation,
)
from .environmental_data import EnvironmentalDataService


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def create_assessment(
    inputs: AssessmentRequest,
    *,
    location_resolver: LocationResolver | None = None,
    rainfall_provider: RainfallProvider | None = None,
    groundwater_provider: GroundwaterProvider | None = None,
    soil_provider: SoilProvider | None = None,
    hydrogeology_provider: HydrogeologyProvider | None = None,
    environmental_data_service: EnvironmentalDataService | None = None,
) -> AssessmentResponse:
    location_query = LocationQuery(
        location=inputs.location,
        latitude=inputs.latitude,
        longitude=inputs.longitude,
        state=inputs.state,
        district=inputs.district,
    )
    environmental_data = (
        environmental_data_service
        or EnvironmentalDataService(
            location_resolver=location_resolver,
            rainfall_provider=rainfall_provider,
            groundwater_provider=groundwater_provider,
            soil_provider=soil_provider,
            hydrogeology_provider=hydrogeology_provider,
        )
    ).collect(location_query)
    location_resolution = environmental_data.location_resolution
    normalized_location = location_resolution.location
    rainfall_lookup = environmental_data.rainfall
    groundwater_lookup = environmental_data.groundwater
    soil_lookup = environmental_data.soil
    hydrogeology_lookup = environmental_data.hydrogeology
    environmental_profile = environmental_data.ar_profile()
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

    monthly_normal = rainfall_record.monthly_normal if rainfall_record else None
    storage = assess_storage_size(
        monthly_rainfall_mm=(
            monthly_normal.values_mm if usable_rainfall and monthly_normal else None
        ),
        roof_area=AreaSquareMeters(inputs.roofAreaM2),
        runoff_coefficient=(
            RunoffCoefficient(coefficient_value)
            if coefficient_value is not None
            else None
        ),
        monthly_demand=(
            VolumeLitres(inputs.monthlyRainwaterDemandLitres)
            if inputs.monthlyRainwaterDemandLitres is not None
            else None
        ),
    )
    recharge_periods = ()
    recharge_supply = None
    recharge_overflow = None
    if (
        inputs.storageCapacityLitres is not None
        and monthly_normal is not None
        and coefficient_value is not None
        and inputs.monthlyRainwaterDemandLitres is not None
    ):
        actual_storage = simulate_storage(
            monthly_rainfall_mm=monthly_normal.values_mm,
            roof_area=AreaSquareMeters(inputs.roofAreaM2),
            runoff_coefficient=RunoffCoefficient(coefficient_value),
            monthly_demand=VolumeLitres(inputs.monthlyRainwaterDemandLitres),
            tank_capacity=VolumeLitres(inputs.storageCapacityLitres),
        )
        recharge_periods = actual_storage.periods
        recharge_supply = actual_storage.total_supplied_litres
        recharge_overflow = actual_storage.total_overflow_litres
    recharge_quantity = assess_recharge_quantity(
        annual_harvest_litres=(
            sum(period.inflow_litres for period in recharge_periods)
            if recharge_periods
            else None
        ),
        annual_demand_supplied_litres=recharge_supply,
        annual_overflow_litres=recharge_overflow,
        catchment_losses_litres=(
            harvest.estimated_losses.value if harvest is not None else None
        ),
        ending_storage_litres=(
            recharge_periods[-1].storage_end_litres if recharge_periods else None
        ),
    )
    user_groundwater_has_metadata = all(
        (
            inputs.groundwaterObservationDate,
            inputs.groundwaterObservationSeason,
            inputs.groundwaterObservationMethod,
            inputs.groundwaterSource,
        )
    )
    provider_groundwater = groundwater_lookup.observation
    groundwater_has_metadata = (
        provider_groundwater is not None or user_groundwater_has_metadata
    )
    groundwater_depth = (
        provider_groundwater.depth_below_ground_level_m
        if provider_groundwater is not None
        else inputs.groundwaterDepthM
    )
    groundwater_season = (
        provider_groundwater.season
        if provider_groundwater is not None
        else inputs.groundwaterObservationSeason
    )
    if provider_groundwater is not None:
        groundwater_reason = (
            f"A CGWB observation from {provider_groundwater.station_name} is available "
            f"at an approximate distance of {provider_groundwater.distance_from_property_m} m. "
            "It is regional evidence, not the property's exact water level."
        )
    elif user_groundwater_has_metadata:
        groundwater_reason = (
            "A user-provided observation includes date, season, method and source, but "
            "has not been independently verified."
        )
    else:
        groundwater_reason = groundwater_lookup.message
    measured_infiltration = (
        soil_lookup.information is not None
        and soil_lookup.information.measured_infiltration_rate_mm_per_hr is not None
    )
    has_soil_evidence = soil_lookup.information is not None
    hydrogeology_available = all(
        status in {DataStatus.DATA_AVAILABLE, DataStatus.DATA_STALE}
        for status in (
            hydrogeology_lookup.geology_status,
            hydrogeology_lookup.aquifer_status,
        )
    )
    feasibility = evaluate_feasibility(
        groundwater_depth_m_bgl=groundwater_depth,
        groundwater_has_observation_metadata=groundwater_has_metadata,
        groundwater_observation_season=groundwater_season,
        groundwater_data_stale=groundwater_lookup.status is DataStatus.DATA_STALE,
        recharge_water_litres=recharge_quantity.potential_recharge_litres_per_year,
        has_infiltration_evidence=has_soil_evidence,
        infiltration_is_property_measured=measured_infiltration,
        has_hydrogeology_evidence=hydrogeology_available,
        water_quality_status=WaterQualityStatus(inputs.waterQualityStatus.value),
        available_ground_area_m2=inputs.availableGroundAreaM2,
        groundwater_reason=groundwater_reason,
        infiltration_reason=soil_lookup.message,
        hydrogeology_reason=hydrogeology_lookup.message,
    )
    hydrogeology_information = hydrogeology_lookup.information
    regional_methodology_id = (
        hydrogeology_information.aquifer_characteristics.get("arMethodologyRegion")
        if hydrogeology_information
        else None
    )
    structure_selection = select_structure(
        feasibility,
        state=(normalized_location.state if normalized_location else inputs.state),
        geology=(hydrogeology_information.geology if hydrogeology_information else None),
        lithology=(hydrogeology_information.lithology if hydrogeology_information else None),
        groundwater_depth_m_bgl=groundwater_depth,
        building_has_basement=inputs.buildingHasBasement,
        roof_area_m2=inputs.roofAreaM2,
        available_ground_area_m2=inputs.availableGroundAreaM2,
        regional_methodology_id=regional_methodology_id,
    )
    structure_sizing = assess_structure_size(
        structure_selection,
        roof_area_m2=inputs.roofAreaM2,
        available_ground_area_m2=inputs.availableGroundAreaM2,
        available_recharge_water_litres=(
            recharge_quantity.potential_recharge_litres_per_year
        ),
        post_monsoon_groundwater_depth_m=(
            groundwater_depth if groundwater_season and "MONSOON" in groundwater_season.upper() else None
        ),
        aquifer_intake_zone_verified=False,
    )

    warnings: list[str] = []
    if rainfall_lookup.status is DataStatus.DATA_STALE:
        warnings.append(rainfall_lookup.message)
    elif rainfall_lookup.status is not DataStatus.DATA_AVAILABLE:
        warnings.append(rainfall_lookup.message)
    if coefficient_lookup.status is not DataStatus.DATA_AVAILABLE:
        warnings.append(coefficient_lookup.message)
    if storage.status is not StorageSizingStatus.SIZE_AVAILABLE:
        warnings.append(storage.message)
    warnings.extend([recharge_quantity.message, *feasibility.reasons])
    if structure_sizing.status != "INDICATIVE_DESIGN_AVAILABLE":
        warnings.append(structure_sizing.message)
    warnings.extend(
        [
            groundwater_lookup.message,
            soil_lookup.message,
            hydrogeology_lookup.message,
        ]
    )

    source_ids = _unique(
        [
            "CGWB_MANUAL_AR_2007",
            "BIS_IS_15797_2008",
            *storage.source_ids,
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
            *(
                provider_groundwater.provenance.source_ids
                if provider_groundwater is not None
                else []
            ),
            *(
                soil_lookup.information.provenance.source_ids
                if soil_lookup.information is not None
                else []
            ),
            *(
                hydrogeology_lookup.information.provenance.source_ids
                if hydrogeology_lookup.information is not None
                else []
            ),
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
                    locality=normalized_location.locality,
                    district=normalized_location.district,
                    state=normalized_location.state,
                    postalCode=normalized_location.postal_code,
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
            sizingDesignPeriod=storage.design_period,
            sizingRainfallResolution=storage.rainfall_resolution,
            sizingRainfallReferencePeriod=(
                monthly_normal.reference_period if monthly_normal else None
            ),
            sizingRainfallSourceUrls=(
                list(monthly_normal.source_urls) if monthly_normal else []
            ),
            sizingRainfallSourceRecords=(
                list(monthly_normal.source_records) if monthly_normal else []
            ),
            demandUsedLitresPerMonth=storage.demand_used_litres_per_month,
            estimatedSupplyLitres=storage.estimated_supply_litres,
            estimatedOverflowLitres=storage.estimated_overflow_litres,
            demandMetPercent=storage.demand_met_percent,
            depletionMonths=list(storage.depletion_months),
            sizingAssumptions=list(storage.assumptions),
            storagePeriods=[
                StoragePeriodResponse(
                    month=period.month,
                    rainfallMm=period.rainfall_mm,
                    inflowLitres=period.inflow_litres,
                    demandLitres=period.demand_litres,
                    cumulativeSurplusLitres=period.cumulative_surplus_litres,
                    suppliedLitres=period.supplied_litres,
                    unmetDemandLitres=period.unmet_demand_litres,
                    overflowLitres=period.overflow_litres,
                    storageEndLitres=period.storage_end_litres,
                )
                for period in storage.periods
            ],
        ),
        artificialRecharge=ArtificialRechargeResult(
            potentialRechargeLitresPerYear=(
                recharge_quantity.potential_recharge_litres_per_year
            ),
            recommendedStructure=(
                StructureRecommendation(
                    type=structure_selection.recommended_structure,
                    displayName={
                        "RECHARGE_TRENCH": "Recharge Trench",
                        "TRENCH_WITH_RECHARGE_WELL": "Trench with Recharge Well",
                        "RECHARGE_WELL": "Recharge Well",
                    }[structure_selection.recommended_structure],
                )
                if structure_selection.recommended_structure
                else None
            ),
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
            quantityMethodId=recharge_quantity.method_id,
            annualHarvestLitres=recharge_quantity.annual_harvest_litres,
            annualDemandSuppliedLitres=(
                recharge_quantity.annual_demand_supplied_litres
            ),
            annualOverflowLitres=recharge_quantity.annual_overflow_litres,
            catchmentLossesLitres=recharge_quantity.catchment_losses_litres,
            endingStorageLitres=recharge_quantity.ending_storage_litres,
            quantityAssumptions=list(recharge_quantity.assumptions),
            quantityMissingInputs=list(recharge_quantity.missing_inputs),
            conditionsPassed=list(feasibility.conditions_passed),
            conditionsFailed=list(feasibility.conditions_failed),
            conditionsRequiringVerification=list(
                feasibility.conditions_requiring_verification
            ),
            missingData=list(feasibility.missing_data),
            fieldTestsRecommended=list(feasibility.field_tests_recommended),
            structureSelectionStatus=structure_selection.status,
            alternativeStructures=list(structure_selection.alternative_structures),
            selectionReasons=list(structure_selection.selection_reasons),
            rejectedStructures=[
                RejectedStructureResponse(
                    structure=item.structure,
                    reason=item.reason,
                    sourceIds=list(item.source_ids),
                )
                for item in structure_selection.rejected_structures
            ],
            structureMissingInputs=list(structure_selection.missing_inputs),
            sizingStatus=structure_sizing.status,
            sizingMethodId=structure_sizing.method_id,
            requiredFootprintM2=structure_sizing.required_footprint_m2,
            filterMedia=list(structure_sizing.filter_media),
            sizingDesignInputs=structure_sizing.design_inputs,
            sizingAssumptions=list(structure_sizing.assumptions),
            fieldVerificationRequired=list(
                structure_sizing.field_verification_required
            ),
            sizingMissingInputs=list(structure_sizing.missing_inputs),
            sourceIds=_unique(
                [
                    *feasibility.source_ids,
                    *recharge_quantity.source_ids,
                    *structure_selection.source_ids,
                    *structure_sizing.source_ids,
                    *(
                        provider_groundwater.provenance.source_ids
                        if provider_groundwater is not None
                        else []
                    ),
                    *(
                        soil_lookup.information.provenance.source_ids
                        if soil_lookup.information is not None
                        else []
                    ),
                    *(
                        hydrogeology_lookup.information.provenance.source_ids
                        if hydrogeology_lookup.information is not None
                        else []
                    ),
                ]
            ),
            environmentalProfile=environmental_profile,
        ),
        rtrwhSuitability="SUITABLE" if harvest else "NOT_ASSESSED",
        dataCompleteness=(
            "GOOD"
            if harvest
            and storage.status is StorageSizingStatus.SIZE_AVAILABLE
            and feasibility.status.value in {"ELIGIBLE", "CONDITIONALLY_ELIGIBLE"}
            and structure_selection.recommended_structure is not None
            and structure_sizing.status in {"INDICATIVE_DESIGN_AVAILABLE", "PARTIAL_INDICATIVE_DESIGN"}
            else "LIMITED"
            if harvest
            else "INSUFFICIENT"
        ),
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
        environmentalData=EnvironmentalDataEvidence(
            locationStatus=location_resolution.status,
            rainfall=EnvironmentalProviderEvidence(
                status=rainfall_lookup.status,
                evidenceAvailable=rainfall_record is not None,
                message=rainfall_lookup.message,
                sourceIds=([rainfall_record.source_id] if rainfall_record else []),
            ),
            groundwater=EnvironmentalProviderEvidence(
                status=groundwater_lookup.status,
                evidenceAvailable=provider_groundwater is not None,
                message=groundwater_lookup.message,
                sourceIds=(
                    list(provider_groundwater.provenance.source_ids)
                    if provider_groundwater
                    else []
                ),
            ),
            soil=EnvironmentalProviderEvidence(
                status=soil_lookup.status,
                evidenceAvailable=soil_lookup.information is not None,
                message=soil_lookup.message,
                sourceIds=(
                    list(soil_lookup.information.provenance.source_ids)
                    if soil_lookup.information
                    else []
                ),
            ),
            hydrogeology=EnvironmentalProviderEvidence(
                status=hydrogeology_lookup.status,
                evidenceAvailable=bool(
                    hydrogeology_lookup.information or hydrogeology_lookup.features
                ),
                message=hydrogeology_lookup.message,
                sourceIds=sorted(
                    {
                        source_id
                        for feature in hydrogeology_lookup.features
                        for source_id in feature.provenance.source_ids
                    }
                    | (
                        set(hydrogeology_lookup.information.provenance.source_ids)
                        if hydrogeology_lookup.information
                        else set()
                    )
                ),
                componentStatuses={
                    "geology": hydrogeology_lookup.geology_status,
                    "geomorphology": hydrogeology_lookup.geomorphology_status,
                    "aquifer": hydrogeology_lookup.aquifer_status,
                    "groundwaterProspect": (
                        hydrogeology_lookup.groundwater_prospect_status
                    ),
                },
            ),
        ),
        warnings=_unique(warnings),
        sources=citations_for(*source_ids),
    )
