# Engineering limitations

The application now exposes these limitations rather than covering them with demo values:

- IMD's 1971-2020 district annual and monthly rainfall normals are committed as an imported, versioned cache. They represent district-scale climatology, not property-scale measurement, current rainfall, a design storm or a year-by-year rainfall series.
- Text location resolution currently depends on the public OpenStreetMap Nominatim service. It can be unavailable or return several candidates; provider rank/count are exposed, and failures stop rainfall/RTRWH calculation. API clients can supply coordinates directly. A production deployment should review public-service usage limits or operate/configure an appropriate geocoder.
- The imported IMD web layer contains 696 features as accessed on 2026-08-13. Administrative boundaries/names and IMD's published product may change; refreshes must be reviewed and versioned rather than silently overwriting provenance.
- CGWB Manual Table 7.2 supports concrete, tiled and GI-sheet coefficients. “Other” and “Don't know” remain unavailable; the metal option is deliberately restricted to GI sheet.
- The CGWB worked-example coefficient is not generalized beyond its published example. The manual's separate 0.9 heavy-rain gutter-design assumption is also not used as a generic annual coefficient (the GI-sheet value happens to be 0.9 for a different, explicitly cited reason).
- Storage capacity is returned only when all 12 IMD monthly normals and an explicit positive user-entered monthly demand are available. The IRICEN July-to-June cumulative-surplus method uses constant monthly demand and normal rainfall; its performance output is not a probabilistic reliability claim, does not model daily variability, and is not optimized for varying end uses or reserves.
- The homeowner soil category is descriptive and is not an infiltration/permeability measurement.
- Groundwater depth entered by the homeowner is user-provided. Unless observation date, season, method and source are supplied, it is not treated as a time-resolved measurement. It still lacks spatial uncertainty unless linked to an official/provider observation.
- A limited, stale CGWB November 2022 groundwater cache currently contains one cross-checked Bengaluru Urban station. It is a nearby observation, not a property measurement; other districts return unsupported rather than receiving a fallback depth.
- The official NWIC soil and NWIC/GSI/Bhuvan hydrogeology service families are registered, but no reviewed coordinate-level soil, geology, geomorphology, groundwater-prospect or aquifer feature is currently imported. Those fields remain unavailable.
- Recharge-available water is calculated only when the IRICEN monthly storage simulation is complete. It is the simulated tank overflow after supplied water and retained storage, not a generic fraction of annual harvest and not a claim of actual aquifer recharge.
- Recharge feasibility does not use HIGH/MEDIUM/LOW scores. It evaluates explicit failure, missing-evidence and field-verification conditions. The only national numeric exclusion currently encoded is CGWB's post-monsoon water-level warning for depths shallower than 3 m bgl.
- Structure selection and sizing currently implement only CGWB's location-specific standard designs for NCT Delhi. The Delhi applicability conditions and dimension tables are not generalized to other states.
- The trench-with-recharge-well chamber table is known, but a complete numeric design remains unavailable without a field-confirmed granular/fractured intake zone and post-monsoon well-termination basis.
- GEC-2015 and the Master Plan are not used as household sizing formulas. They operate at groundwater assessment/planning scales and may contain state-specific assumptions.
- The result remains preliminary and cannot replace field investigation, water-quality safeguards, applicable building/by-law requirements or professional design.
