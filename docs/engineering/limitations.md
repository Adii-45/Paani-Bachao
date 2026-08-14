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
- No CGWB/NAQUIM or documented Bhuvan feature is currently resolved for the property. Aquifer, geology, geomorphology and groundwater-quality evidence are therefore missing.
- Rechargeable water cannot be calculated without allocation/use/overflow data and site/aquifer acceptance evidence. No generic recharge fraction is applied.
- Recharge feasibility does not use HIGH/MEDIUM/LOW scores. It reports `INSUFFICIENT_DATA` until every mandatory engineering criterion can be evaluated.
- Recharge pits, trenches, tubewells and recharge wells are recognized as CGWB-listed urban techniques, but the engine does not select among them without an applicable structure-specific method and site evidence.
- No numeric recharge-structure dimensions are returned. IS 15792:2008 and its listed amendment require lawful detailed review, and structure-specific CGWB applicability/inputs must be established first.
- GEC-2015 and the Master Plan are not used as household sizing formulas. They operate at groundwater assessment/planning scales and may contain state-specific assumptions.
- The result remains preliminary and cannot replace field investigation, water-quality safeguards, applicable building/by-law requirements or professional design.
