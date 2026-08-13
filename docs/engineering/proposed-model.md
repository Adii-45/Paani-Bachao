# Source-backed assessment model

This document defines the implementation boundary after the source audit. It deliberately returns unavailable states where the repository does not contain the authoritative data or site measurements required for a defensible answer.

## Calculation and decision flow

```text
user location / optional coordinates
        |
        v
versioned IMD-normal rainfall provider ----> DATA_UNAVAILABLE when no official record exists
        |
roof area + source-backed roof coefficient
        |
        v
gross rainfall volume and harvestable rooftop runoff
        |
        +----> storage strategy
        |         event rainfall / rainfall distribution / demand missing
        |         => INSUFFICIENT_DATA_FOR_SIZING
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

The current five-city values are removed from the primary engine. The replacement is a provider over normalized, versioned IMD records. A record must carry:

- `rainfall_mm`;
- `statistic_type` (for this method, a long-period/normal annual statistic);
- `reference_period`;
- `spatial_resolution` and official location/feature identifier;
- source dataset title/version/record;
- retrieval/import timestamp;
- data-quality category.

The IMD public API's current observed/daily rainfall is not silently treated as a long-period annual normal. Until an appropriate official dataset is imported, the provider returns `DATA_UNAVAILABLE` or `UNSUPPORTED_LOCATION`. The ingestion boundary accepts officially obtained tabular data and never manufactures missing records.

## Runoff coefficients

CGWB Manual Table 7.2 (document page 118) publishes GI sheet 0.90, asbestos 0.80, tiled 0.75 and concrete 0.70. The current API maps RCC/concrete to the concrete entry, tiles to tiled, and the former broad metal category only to GI sheet; the frontend makes that restriction explicit. “Other” and “Don't know” remain unavailable. Asbestos is not added because it is not a current supported input.

Each coefficient record includes its published value, condition, selection method and source ID. If a future source publishes a range but property inputs do not justify choosing a point value, the calculation must remain unavailable or expose the range; it must not silently choose its midpoint. The CGWB Manual's separate 0.9 heavy-rain gutter-design assumption is not used as an annual generic coefficient.

## Storage sizing

Annual harvesting potential and storage capacity are separate outputs. The CGWB Manual §7.2.7.2 states that urban storage may be based on rainfall in a single event, and §7.3.2 notes that rainfall distribution affects storage requirements. A demand/reliability strategy additionally needs intended use, demand and dry-period/reliability inputs.

The current inputs do not contain an official event-rainfall series, demand or allocation information. The primary strategy therefore returns:

```text
INSUFFICIENT_DATA_FOR_SIZING
```

with the missing inputs and applicable source IDs. It does not use the former 6%, 500 L increment or 20,000 L cap.

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
| Live external data | None required for deterministic assessment; provider interfaces isolate future services |
| Official periodically imported data | IMD normal rainfall and future CGWB/NAQUIM/NRSC layers, normalized and versioned |
| Cached data | Only previously ingested official records with original version/date and retrieval timestamp |
| Source-backed configuration | Source registry and future coefficient/decision records with clause/page provenance |
| Derived calculation | Unit-safe rainfall volume and rooftop harvest when required evidence exists |
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

The existing frontend can submit the current request and render null/unavailable values, so no form, route, styling or layout change is required for the backend transition. A minimal additive result rendering change may be made only to expose the new feasibility reasons and source provenance. No page or visual redesign is planned.
