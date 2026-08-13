# Engineering source audit

Audit date: 2026-08-13

This audit is the evidence gate for replacing the demo assessment engine. `KEEP` means the current implementation is supported as written. `REPLACE` means a source-backed implementation is available. `REMOVE` means the value or rule has no adequate provenance and must not be used by the primary assessment. `RESEARCH_REQUIRED` means an authoritative source or licensed dataset still has to be obtained before the feature can return a numeric result.

## Current-assumption audit

| Parameter / rule | Current value | Current file | Current logic | Current source | Authoritative replacement source | Action |
| --- | --- | --- | --- | --- | --- | --- |
| Active ruleset | `demo` by default | `backend/app/rules/loader.py` | `RAINASSESS_RULESET` defaults to `demo` | None | Evidence policy in this audit | REPLACE |
| Annual rainfall: Bengaluru | 970 mm/year | `backend/app/data/demo/rainfall.json` | Exact city/alias lookup | Explicitly marked demo/not validated | IMD long-period normal rainfall dataset, with period and spatial resolution | REMOVE |
| Annual rainfall: Chennai | 1400 mm/year | Same | Same | Explicitly marked demo/not validated | IMD long-period normal rainfall dataset | REMOVE |
| Annual rainfall: Delhi | 800 mm/year | Same | Same | Explicitly marked demo/not validated | IMD long-period normal rainfall dataset | REMOVE |
| Annual rainfall: Hyderabad | 850 mm/year | Same | Same | Explicitly marked demo/not validated | IMD long-period normal rainfall dataset | REMOVE |
| Annual rainfall: Mumbai | 2200 mm/year | Same | Same | Explicitly marked demo/not validated | IMD long-period normal rainfall dataset | REMOVE |
| Rainfall location aliases/PIN codes | Five city names and one PIN per city | Same | Normalized string equality | None | Official dataset identifiers and coordinate/admin-boundary lookup | REMOVE |
| RCC runoff coefficient | 0.80 | `backend/app/data/demo/runoff_coefficients.json` | Direct material lookup | Explicitly marked demo/not validated | CGWB Manual (2007), Table 7.2, document page 118: concrete roof 0.70 | REPLACE |
| Tile runoff coefficient | 0.75 | Same | Same | Explicitly marked demo/not validated | CGWB Manual Table 7.2: tiled roof 0.75 | REPLACE |
| Metal runoff coefficient | 0.85 | Same | Same | Explicitly marked demo/not validated | CGWB Manual Table 7.2: GI sheet 0.90; UI category must be restricted to GI sheet | REPLACE |
| Other/unknown coefficient | `null` | Same | Returns unavailable | No coefficient claimed | No replacement needed until a supported category is added | KEEP |
| Harvestable-volume equation | area × annual rainfall × coefficient | `backend/app/calculations/rtrwh.py` | 1 mm over 1 m² is treated as 1 litre; result rounded to 2 decimals | Code comment only | CGWB, *Manual on Artificial Recharge of Ground Water* (2007), §7.2.7.1 and §7.3.1, document page 119 | REPLACE |
| Storage fraction | 6% of annual potential | `backend/app/data/demo/rtrwh_sizing.json` | Multiplies annual yield by 0.06 | Explicitly marked demo/not validated | CGWB Manual §7.2.7.2 and §7.3.2 require event rainfall/distribution; demand-based strategies require demand and reliability inputs | REMOVE |
| Storage rounding | Round up to 500 L | Same | Mathematical ceiling | Explicitly marked demo/not validated | No universal authoritative rounding rule identified | REMOVE |
| Storage cap | 20,000 L | Same | Caps recommendation | Explicitly marked demo/not validated | No universal authoritative cap identified | REMOVE |
| Sandy soil score/fraction | score 3; fraction 0.75 | `backend/app/data/demo/recharge_rules.json` | Adds score; multiplies harvest by fraction | Explicitly marked demo/not validated | Site-specific infiltration/permeability and hydrogeological evidence under CGWB investigation guidance | REMOVE |
| Sandy-loam score/fraction | score 3; fraction 0.65 | Same | Same | Explicitly marked demo/not validated | Same | REMOVE |
| Loam score/fraction | score 2; fraction 0.50 | Same | Same | Explicitly marked demo/not validated | Same | REMOVE |
| Clayey score/fraction | score 1; fraction 0.25 | Same | Same | Explicitly marked demo/not validated | Same | REMOVE |
| Rocky score/fraction | score 0; fraction 0.10 | Same | Same | Explicitly marked demo/not validated | Geology, fractures, weathering, aquifer and infiltration evidence; a label of “rocky” is insufficient | REMOVE |
| Groundwater-depth bands | 0–&lt;3: 0; 3–&lt;8: 1; 8–&lt;20: 2; ≥20 m: 1 | Same | Adds band score | Explicitly marked demo/not validated | Time-stamped CGWB/NAQUIM water-level observations plus source-specific feasibility criteria | REMOVE |
| Available-area bands | 0–&lt;4: 0; 4–&lt;10: 1; ≥10 m²: 2 | Same | Adds band score | Explicitly marked demo/not validated | Structure-specific footprint/design requirements after a structure is technically applicable | REMOVE |
| Recharge classification | ≥6 HIGH; ≥4 MEDIUM; ≥2 LOW; ≥0 NOT_RECOMMENDED | Same | Sum of soil, depth and area scores | Explicitly marked demo/not validated | Explainable criterion outcomes: eligible, conditionally eligible, not eligible, or insufficient data | REMOVE |
| Recharge volume | annual harvest × soil fraction | `backend/app/services/assessment.py` | Uses demo fraction as recharge fraction | None beyond demo soil table | Water balance using documented allocations/losses and site/aquifer capacity | REMOVE |
| Trench selection | HIGH/MEDIUM and area ≥9 m² | `backend/app/data/demo/ar_structures.json` | First matching rule | Explicitly marked demo/not validated | Structure-specific CGWB methodology applied to verified site/hydrogeological inputs | REMOVE |
| Trench dimensions | 3 × 1 × 1.5 m | Same | Copied verbatim from rule | Explicitly marked demo/not validated | Structure-specific design calculation and source applicability | REMOVE |
| Pit selection | HIGH/MEDIUM/LOW and area ≥4 m² | Same | Second matching rule | Explicitly marked demo/not validated | Structure-specific CGWB methodology | REMOVE |
| Pit dimensions | 2 × 2 × 2 m | Same | Copied verbatim from rule | Explicitly marked demo/not validated | Structure-specific design calculation and source applicability | REMOVE |
| Input upper bounds | area ≤100,000 m²; depth ≤1,000 m | `backend/app/schemas.py` | API abuse/sanity validation | No engineering source | Keep only as software safety limits, explicitly not engineering criteria | KEEP |
| Soil dropdown labels | sandy, sandy loam, loam, clayey, rocky, unknown | `backend/app/schemas.py` and frontend | User supplies broad category | No measurement/source metadata | Replace as decision input with measured/authoritative soil/infiltration evidence; may remain descriptive only | RESEARCH_REQUIRED |
| User-entered groundwater depth | non-negative metres | Same | Treated as exact current depth | User supplied, without date/method | Normalized observation with date, season, method, source and spatial uncertainty | REPLACE |

## Source matrix

| Requirement | Authoritative source | Document/dataset | Formula/rule/data supplied | Integration method | Confidence |
| --- | --- | --- | --- | --- | --- |
| Rooftop runoff volume | CGWB | *Manual on Artificial Recharge of Ground Water* (2007), §7.2.7.1 and §7.3.1, document page 119 | rainfall (mm) × roof area (m²) × roof runoff coefficient; mean annual rainfall may represent an average year | Source-backed calculation with explicit units and provenance | High |
| Storage sizing | CGWB; BIS | CGWB Manual §7.2.7.2/§7.3.2; IS 15797:2008 | Storage depends on rainfall per spell/distribution; BIS standard governs rooftop harvesting guidance | Named sizing strategies only when their required input series/demand data exist; otherwise insufficient data | High for insufficiency decision; standard text still required for further implementation |
| Standard status | BIS | WRD 3 Programme of Work | IS 15797:2008 reaffirmed January 2023; IS 15792:2008 reaffirmed January 2023 with one amendment | Registry metadata; acquire licensed standard/amendment before encoding detailed clauses | High |
| Artificial recharge investigation/design | CGWB | *Manual on Artificial Recharge of Ground Water* (2007) and *Guide on Artificial Recharge to Ground Water* | Requires investigation and structure selection appropriate to hydrogeological setting | Criterion-based feasibility with missing-data reporting; no additive score | High |
| National recharge planning | CGWB | *Master Plan for Artificial Recharge to Groundwater in India* (2020) | Macro/state planning based on hydrogeology, groundwater levels/trends, subsurface storage and surplus runoff | Context only; never directly treated as universal household sizing rules | High |
| Dynamic groundwater resource estimation | CGWB | GEC-2015 methodology | Assessment-unit groundwater-resource estimation | Context/provider metadata only; not household structure sizing | High |
| Aquifer/geology/quality | CGWB | NAQUIM/NAQUIM 2.0 aquifer maps and management plans | Aquifer geometry/properties, water levels, resource availability and quality at stated mapping resolution | Periodic official import/provider, retaining report/feature identifiers and resolution | High, but coverage/granularity varies |
| Groundwater prospects/thematic GIS | NRSC/ISRO | Bhuvan/Bhuvan Bhujal thematic services | Geomorphology, lithology and groundwater-prospect information where published/authorized | Documented OGC/download provider only; no scraping; unsupported where access is restricted | Medium pending layer-by-layer service verification |
| Normal rainfall | IMD | Official long-period normal rainfall data obtained through IMD data services/supply channels | Normal rainfall with reference period and station/grid/district resolution | Versioned ingestion into normalized local records; no current-daily substitute | High when an official dataset is supplied; currently unavailable in repository |
| Current observed rainfall | IMD | IMD public district/station rainfall APIs | Current/daily/cumulative observed products | Not used as a substitute for long-period annual normal; possible future separate provider | High, not applicable to current annual-potential method |
| Material-specific roof coefficients | CGWB | *Manual on Artificial Recharge of Ground Water* (2007), Table 7.2, document page 118 | GI sheet 0.90, asbestos 0.80, tiled 0.75, concrete 0.70 | Source-backed records; enable only matching UI categories and expose the published condition | High |
| Structure-specific sizing | CGWB; BIS IS 15792:2008 | Structure-specific guidance plus site investigation | Required inputs and valid application ranges differ by structure | Implement separately per structure only after clauses and required site data are available | Low/currently unresolved for automated residential sizing |

## Primary references

- CGWB, *Manual on Artificial Recharge of Ground Water* (2007): https://cgwb.gov.in/sites/default/files/MainLinks/Manual-Artificial-Recharge.pdf
- CGWB, *Guide on Artificial Recharge to Ground Water*: https://cgwb.gov.in/cgwbpnm/public/uploads/documents/16861384061006484074file.pdf
- CGWB, *Master Plan for Artificial Recharge to Groundwater in India* (2020): https://cgwb.gov.in/cgwbpnm/public/uploads/documents/168613326251844776file.pdf
- CGWB, Ground Water Resource Assessment / GEC methodology: https://cgwb.gov.in/en/ground-water-resource-assessment-0
- CGWB, Aquifer Mapping / NAQUIM: https://cgwb.gov.in/en/aquifer-mapping
- IMD public API reference: https://api.imd.gov.in/public/api_reference.html
- IMD rainfall information: https://mausam.imd.gov.in/responsive/rainfallinformation_swd.php?msg=M
- BIS WRD 3 Programme of Work: https://www.services.bis.gov.in/php/BIS_2.0/bisconnect/pow_new/Pow/download_pow_pdf_dept_commtt/72/92/
- NRSC/ISRO Bhuvan WMS guidance: https://bhuvan.nrsc.gov.in/wiki/index.php/How_to_use_WMS_services
- NRSC/ISRO Bhuvan water-sector information: https://bhuvan.nrsc.gov.in/wiki/index.php/Water_Sector

## Audit decision

The demo rules are not suitable as a default or fallback and are removed. The replacement engine may calculate annual rooftop harvest only when both an official rainfall record and a matching Table 7.2 roof coefficient are available. Storage sizing, recharge feasibility, rechargeable quantity, structure selection and dimensions must return explicit insufficient-data or unsupported states until their source-specific required inputs are present.
