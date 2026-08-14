# Engineering limitations

The application now exposes these limitations rather than covering them with demo values:

- IMD's 1971-2020 district annual and monthly rainfall normals are committed as an imported, versioned cache. They represent district-scale climatology, not property-scale measurement, current rainfall, a design storm or a year-by-year rainfall series.
- Text location resolution currently depends on the public OpenStreetMap Nominatim service. Successful and ambiguous results use a bounded process-local TTL cache; timeouts, rate limits, malformed responses and zero results are not cached as successful locations. Equally ranked matches with different coordinates return `AMBIGUOUS`, and failures stop rainfall/RTRWH calculation. API clients can supply coordinates directly. A production deployment should review public-service usage limits or operate/configure an appropriate geocoder; the process-local cache is not a shared production cache.
- The imported IMD web layer contains 696 features as accessed on 2026-08-13. Administrative boundaries/names and IMD's published product may change; refreshes must be reviewed and versioned rather than silently overwriting provenance.
- CGWB Manual Table 7.2 supports concrete, tiled and GI-sheet coefficients. “Other” and “Don't know” remain unavailable; the metal option is deliberately restricted to GI sheet.
- The CGWB worked-example coefficient is not generalized beyond its published example. The manual's separate 0.9 heavy-rain gutter-design assumption is also not used as a generic annual coefficient (the GI-sheet value happens to be 0.9 for a different, explicitly cited reason).
- Storage capacity is returned only when all 12 IMD monthly normals and an explicit positive user-entered monthly demand are available. The IRICEN July-to-June cumulative-surplus method uses constant monthly demand and normal rainfall; its performance output is not a probabilistic reliability claim, does not model daily variability, and is not optimized for varying end uses or reserves.
- The standard homeowner form does not ask for soil or groundwater technical values.
  Optional API compatibility/field-officer observations are never relabelled as
  authoritative provider measurements.
- The limited November 2024 CGWB cache is stale. It contains nearby observations for
  the reviewed Delhi/Bengaluru slices, not property measurements; freshness and
  distance remain explicit and current field confirmation is mandatory.
- One Jayanagar regional soil proxy and three regional hydrogeology records are
  installed. They do not provide property infiltration, a borehole log, geomorphology
  or groundwater-prospect values. Missing components remain null.
- Recharge-available water is calculated only when the IRICEN monthly storage simulation is complete. It is the simulated tank overflow after supplied water and retained storage, not a generic fraction of annual harvest and not a claim of actual aquifer recharge.
- Recharge feasibility does not use HIGH/MEDIUM/LOW scores. It evaluates explicit failure, missing-evidence and field-verification conditions. The only national numeric exclusion currently encoded is CGWB's post-monsoon water-level warning for depths shallower than 3 m bgl.
- Structure selection/sizing is restricted to the intersecting Hauz Khas Delhi record
  and Jayanagar Bengaluru record. The Delhi table and KSCST table are not generalized
  to the rest of Delhi, Bengaluru, Karnataka or India.
- The trench-with-recharge-well chamber table is known, but a complete numeric design remains unavailable without a field-confirmed granular/fractured intake zone and post-monsoon well-termination basis.
- GEC-2015 and the Master Plan are not used as household sizing formulas. They operate at groundwater assessment/planning scales and may contain state-specific assumptions.
- The result remains preliminary and cannot replace field investigation, water-quality safeguards, applicable building/by-law requirements or professional design.
