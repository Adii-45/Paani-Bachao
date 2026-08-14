# Source-backed assessment model

This document defines the implementation boundary after the source audit. It deliberately returns unavailable states where the repository does not contain the authoritative data or site measurements required for a defensible answer.

## Calculation and decision flow

```text
user location / optional coordinates
        |
        v
replaceable location resolver -> canonical location + latitude/longitude
        |
        v
versioned IMD district-normal provider ----> DATA_UNAVAILABLE when no official record exists
        |
roof area + source-backed roof coefficient
        |
        v
gross rainfall volume and harvestable rooftop runoff
        |
        +----> storage strategy
        |         12 IMD monthly normals + explicit monthly demand
        |         => IRICEN July-to-June cumulative-surplus method
        |         => capacity or an explicit unavailable state
        |
        +----> water-allocation balance
                  storage/use + documented losses + overflow allocation missing
                  => recharge quantity unavailable
                           |
groundwater observation + infiltration + hydrogeology + quality/site constraints
                           |
                           v
                   recharge feasibility criteria
                           |
                           v
              structure selection and per-structure sizing
              only when all source-required inputs are present
```

## Rooftop harvesting

Method ID: `CGWB_MANUAL_2007_RTRWH_ANNUAL_VOLUME`

The CGWB Manual, §7.2.7.1 and §7.3.1 (document page 119), gives:

```text
harvestable volume = rainfall × roof area × roof runoff coefficient
```

With rainfall in millimetres and area in square metres:

```text
1 mm = 0.001 m
1 m³ = 1,000 L
therefore 1 mm × 1 m² = 1 L
```

The engine will expose:

- rainfall and its official dataset provenance;
- roof area and its user-provided provenance;
- coefficient value/range, conditions and provenance;
- gross rainfall volume before the coefficient;
- estimated losses represented by the coefficient;
- harvestable volume;
- method ID and source references;
- explicit assumptions.

No result is calculated when rainfall or a supported coefficient is absent.

## Rainfall

The current five-city values are removed from the primary engine. The replacement is a provider over IMD's **All India Districtwise Rainfall Normals (1971-2020)** annual and January-to-December monthly maps. The committed normalized cache contains the 696 district features published in each accessed official layer. A record carries:

- `rainfall_mm`;
- `statistic_type` (for this method, a long-period/normal annual statistic);
- `reference_period`;
- `spatial_resolution` and official location/feature identifier;
- source dataset title/version/record;
- retrieval/import timestamp;
- data-quality category.
- all 12 monthly normals and their individual source URLs/digests when the monthly
  feature set is complete and administratively consistent with the annual record.

The IMD public API's current observed/daily rainfall is not silently treated as a long-period annual normal. The importer preserves the published district geometry, source feature ID, source URL, 1971-2020 reference period, import timestamp and source-file digest. Assessment-time lookup uses resolved coordinates against that local geometry, with no rainfall network call and no manufactured fallback.

## Location resolution

`LocationResolver` isolates the assessment service from geocoder-specific HTTP code. The current text implementation uses the Nominatim search API with an India country filter and retains the provider's highest-ranked result, candidate count, place ID, importance metadata, coordinates and administrative fields. It does not convert those values into an invented numeric confidence score. API callers may provide coordinates directly; those are clearly marked `USER_PROVIDED_COORDINATES` and are not presented as geocoded facts.

If resolution fails, the service returns `NOT_RESOLVED` or `PROVIDER_UNAVAILABLE`, does not call rainfall lookup, and does not calculate RTRWH potential. Nominatim is a replaceable non-engineering location service; IMD remains the rainfall authority.

## Runoff coefficients

CGWB Manual Table 7.2 (document page 118) publishes GI sheet 0.90, asbestos 0.80, tiled 0.75 and concrete 0.70. The current API maps RCC/concrete to the concrete entry, tiles to tiled, and the former broad metal category only to GI sheet; the frontend makes that restriction explicit. “Other” and “Don't know” remain unavailable. Asbestos is not added because it is not a current supported input.

Each coefficient record includes its published value, condition, selection method and source ID. If a future source publishes a range but property inputs do not justify choosing a point value, the calculation must remain unavailable or expose the range; it must not silently choose its midpoint. The CGWB Manual's separate 0.9 heavy-rain gutter-design assumption is not used as an annual generic coefficient.

## Storage sizing

Annual harvesting potential and storage capacity are separate outputs. The implemented
method is the monthly cumulative-surplus method published in Indian Railways Institute
of Civil Engineering's *Rain Water Harvesting* (November 2022), §2.2.8.1, pages 41-42.
It orders a normal year from July through June, calculates monthly rooftop yield from
rainfall, area and runoff coefficient, subtracts a constant explicit monthly demand,
and selects the maximum positive cumulative surplus as capacity.

The API accepts optional `monthlyRainwaterDemandLitres`. This value is user-provided;
the application does not infer demand or insert a norm. When demand and all 12 official
monthly normals are available, the result includes the recommended capacity and a
finite-tank normal-year simulation (supply, unmet demand, overflow and depletion
months). These are climatological normal-year metrics, not a probabilistic reliability
guarantee. When demand or monthly data are absent, the strategy returns:

```text
INSUFFICIENT_DATA_FOR_SIZING
```

with the missing inputs and applicable source IDs. Zero rainfall and a series with no
positive cumulative surplus also return explicit non-recommendation states. The method
does not use the former 6%, 500 L increment or 20,000 L cap.

## Available water for recharge

The engine distinguishes:

```text
harvestable rooftop runoff
- water allocated to storage/direct use
- separately documented conveyance/first-flush losses not already represented
- other documented allocations
= water potentially available for recharge
```

No loss or allocation percentage is assumed. Because the current request does not provide a complete allocation plan, `potentialRechargeLitresPerYear` is unavailable rather than being derived from a soil label.

## Recharge feasibility

The additive score is removed from the primary model. The feasibility evaluator reports criterion outcomes and a derived overall state:

- `ELIGIBLE` only if every mandatory, source-defined criterion passes;
- `CONDITIONALLY_ELIGIBLE` only when an authoritative rule explicitly supports a conditional outcome;
- `NOT_ELIGIBLE` when a source-defined exclusion is established;
- `INSUFFICIENT_DATA` when any mandatory criterion cannot be evaluated.

The initial implementation checks data sufficiency, not invented numeric thresholds. The following evidence is required before a positive engineering conclusion:

- source water quantity after allocations;
- a time-stamped groundwater observation with method/season and uncertainty;
- measured or authoritative infiltration/permeability evidence at known resolution;
- geology, geomorphology and aquifer characteristics;
- groundwater/source-water quality and contamination-risk review;
- site constraints and available footprint.

The current broad soil category and undated user-entered groundwater depth are preserved as user observations but cannot by themselves establish recharge feasibility.

## Structure selection and sizing

CGWB identifies urban options including recharge pits, trenches, tubewells and recharge wells, but listing a structure is not a universal selection rule. Selection must evaluate the complete inputs and applicability conditions of the source-specific methodology. Until that evidence is available, the engine returns no recommended structure and explains the missing inputs.

Each future structure will have an independent sizing strategy with its own required inputs, formula, valid range, construction/filter constraints and source references. No universal dimension equation is introduced.

## Data architecture

| Category | Current implementation policy |
| --- | --- |
| User input | Roof area, descriptive roof material/soil, undated groundwater-depth estimate and open area; retained as `USER_PROVIDED` and never relabelled as measured |
| Live external data | Nominatim text geocoding when the request does not already contain coordinates; no environmental value comes from it |
| Official periodically imported data | IMD 1971-2020 annual and monthly district normals and future CGWB/NAQUIM/NRSC layers, normalized and versioned |
| Cached data | 696 imported IMD district polygons with annual/monthly normals, original feature IDs, period, URLs, digests and retrieval timestamp |
| Source-backed configuration | Source registry and future coefficient/decision records with clause/page provenance |
| Derived calculation | Unit-safe annual rooftop harvest and conditional IRICEN monthly storage sizing when required evidence exists |
| Assumption/default | Must be source-backed, labelled `ENGINEERING_DEFAULT` or `ASSUMED`, and returned in response provenance; none are silently inserted into inputs |

## External-data failure states

- `DATA_AVAILABLE`
- `DATA_UNAVAILABLE`
- `DATA_STALE`
- `UNSUPPORTED_LOCATION`
- `INSUFFICIENT_DATA`

The provider never falls back to the deleted demo city values. A stale official cache may be returned only with `DATA_STALE`, its original dataset version and timestamps.

## API compatibility

The existing request fields remain accepted. Optional latitude/longitude and administrative identifiers may be added without renaming existing keys. Existing top-level result fields remain available so the current Next.js result page does not break; richer evidence, status, criteria and method fields are additive. Numeric recommendations become `null` when evidence is insufficient.

## Frontend impact statement

The existing frontend keeps its routes and layout. One optional monthly-use input was
added because the selected sizing method cannot operate without explicit demand; the
result page additively renders the method, normal-year metrics and assumptions. No
arbitrary default is pre-populated and no visual redesign is included.
