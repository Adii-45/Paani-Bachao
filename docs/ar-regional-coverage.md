# Artificial Recharge regional coverage

Artificial-recharge coverage is intentionally regional. A real address is always
resolved by the existing location resolver; the application never substitutes a
demo coordinate or city dictionary.

## Currently validated end-to-end areas

### Hauz Khas, Delhi

- Rainfall: IMD district monthly and annual normals (1971–2020).
- Groundwater: CGWB Delhi Ground Water Year Book 2024–25, nearby Hauz Khas
  piezometer, November 2024. The cache is marked stale and must be verified.
- Hydrogeology: CGWB Delhi Zone B regional alluvial setting.
- Structure method: CGWB Delhi standard-design table.
- Expected result: a conditional trench-with-recharge-well recommendation where
  property inputs fit. Chamber dimensions may be shown, but final well depth is
  never inferred without a field-confirmed granular/fractured intake zone.

### Jayanagar, Bengaluru

- Rainfall: IMD Bengaluru Urban district monthly and annual normals (1971–2020).
- Groundwater: CGWB Bengaluru NAQUIM 2.0, Jayanagar monitoring well, November
  2024. The cache is marked stale and must be verified.
- Soil: CGWB regional red lateritic/red, fine-loamy-to-clayey description. This is
  not a measured infiltration rate; a field test is mandatory.
- Hydrogeology: CGWB regional Peninsular Gneissic Complex and weathered/fractured
  aquifer interpretation.
- Structure method: CGWB Bengaluru urban-core applicability guidance plus the
  KSCST residential recharge-well table.
- Expected result: conditional recharge-well options. KSCST geometric table depth
  is shown separately from the unknown final aquifer intake depth.

Greater Kailash II has reviewed groundwater and hydrogeological evidence in the
installed cache, but the current imported IMD polygon cache does not cover the
coordinates. It is therefore **not** listed as end-to-end supported and rainfall,
RTRWH, and AR fail safely there.

## Required property inputs

| Input | Why it remains manual |
| --- | --- |
| Location | Needed by the real resolver and spatial providers. |
| Roof area | Property geometry is not safely inferable from regional datasets. |
| Roof material | Selects the source-backed runoff coefficient. |
| Planned monthly rainwater use | Required by the storage sizing/water balance. |
| Existing or planned tank capacity | Required to simulate actual overflow available for recharge. |
| Available open-ground area | A property-specific physical footprint constraint. |
| Basement presence | Required by the applicable CGWB Delhi design rule; optional elsewhere. |

The homeowner is no longer asked to guess soil type, groundwater depth, water
quality, geology, or aquifer properties. Water quality, current groundwater and
property infiltration remain explicit field-verification requirements.

## Safety and limitations

- Regional maps and nearby wells are not measurements beneath a property.
- Stale groundwater evidence produces a conditional result, never a current fact.
- Missing rainfall stops RTRWH and AR water-balance calculations.
- Total annual roof harvest is not treated as recharge water. Only overflow from
  the finite tank simulation using the entered tank capacity is routable to AR.
- No numeric AR score, soil recharge fraction, or India-wide fallback is used.
- Final construction requires water-quality review, infiltration/percolation
  testing, utility/foundation inspection, and hydrogeological confirmation.

## Production and test data

Production normalized caches contain only records traceable to the source
registry. Synthetic records remain confined to tests and are never loaded as a
runtime fallback.
