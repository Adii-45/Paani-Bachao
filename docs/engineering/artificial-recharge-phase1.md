# Phase 1 artificial-recharge methods

This document describes the production methods implemented for recharge-water
availability, feasibility, structure selection and sizing. The assessment is
preliminary. It does not replace field testing, hydrogeological review, water-quality
testing, local permission or structural design.

## Recharge-available water

Method ID: `IRICEN_STORAGE_OVERFLOW_AVAILABLE_FOR_AR`

The existing IRICEN monthly finite-tank simulation conserves water as:

```text
monthly harvested inflow
= water supplied + tank overflow + change in tank storage
```

Across the July-to-June design year, the engine reports tank overflow as water
**potentially available for routing** to artificial recharge:

```text
available recharge water = sum(monthly tank overflow)
```

The roof runoff coefficient has already represented catchment loss before water enters
the storage simulation. Supplied water and water retained in the tank are not counted as
recharge water. No soil fraction or percentage of annual harvest is applied. The result
does not claim that the site or aquifer can accept the overflow.

Sources: IRICEN, *Rain Water Harvesting* (November 2022), §2.2.8–2.2.8.1,
pages 40–42; CGWB, *Manual on Artificial Recharge of Ground Water* (2007).

## Feasibility

Method: explicit criteria with precedence, never a summed score.

1. An established failure produces `NOT_ELIGIBLE`.
2. Missing critical water-balance, groundwater or hydrogeological evidence produces
   `INSUFFICIENT_DATA`.
3. A field/quality confirmation still required produces `CONDITIONALLY_ELIGIBLE`.
4. Only all passed criteria produce `ELIGIBLE`.

The implemented numeric exclusion is limited to CGWB's February 2025 FAQ statement
that artificial-recharge structures are not recommended where post-monsoon groundwater
level is shallower than 3 m below ground level. A measurement from another season does
not silently pass that check. Missing property infiltration and water-quality evidence
produce named verification requirements rather than inferred values.

## Structure selection and sizing

Method ID: `CGWB_DELHI_STANDARD_RTRWH_DESIGNS`

The only installed structure method is CGWB's *Standard Designs for Adoption of Roof
Top Rainwater Harvesting in Delhi*. It is not generalized outside NCT Delhi.

- A trench without recharge well is considered only for alluvial formation, a
  post-monsoon groundwater depth greater than 5 m and up to 15 m below ground level,
  and a building without a basement.
- A trench with recharge well is considered for alluvial or hard-rock formation where
  post-monsoon groundwater depth is greater than 15 m below ground level.
- The published tables cover roof areas up to 500 m². Dimensions are selected from the
  published roof-area band and are not interpolated.
- The reported internal footprint must fit within the user's available ground area.
- The table's own design basis (0.025 m/hour rainfall intensity, 0.8 runoff coefficient
  and 0.54 m normal monsoon rainfall) is retained as table provenance. Those values are
  not substituted into the separate annual RTRWH calculation.
- A trench-with-well remains unsized until a granular/fractured intake zone is field
  verified. When that evidence exists, the published instruction terminates the well
  2–3 m above the post-monsoon water level.

CGWB explicitly describes the designs as indicative and dependent on site conditions.
The response therefore includes filter media, assumptions and mandatory field checks.
Locations outside Delhi return `UNSUPPORTED_LOCATION_FOR_SELECTION`; they do not receive
a Delhi-derived structure or dimensions.

## Data limitations

The committed production soil and hydrogeology caches currently contain no reviewed
coordinate-level records. Consequently, ordinary runtime assessments remain
`INSUFFICIENT_DATA` for AR even when a storage overflow exists. The deterministic full
integration test injects source-shaped environmental fixtures to verify the complete
software path; it is not evidence that national environmental coverage is installed.
