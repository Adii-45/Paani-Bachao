from typing import Any


def classify_recharge(
    soil_type: str,
    groundwater_depth_m: float,
    available_area_m2: float,
    rules: dict[str, Any],
) -> tuple[str | None, float | None]:
    soil = rules.get("soilRatings", {}).get(soil_type)
    depth_bands = rules.get("groundwaterDepthBands", [])
    area_bands = rules.get("availableAreaBands", [])
    thresholds = rules.get("classificationThresholds", [])
    if soil is None or not depth_bands or not area_bands or not thresholds:
        return None, None

    def band_score(value: float, bands: list[dict[str, Any]]) -> float | None:
        for band in bands:
            if value >= band["minInclusive"] and (
                band.get("maxExclusive") is None or value < band["maxExclusive"]
            ):
                return float(band["score"])
        return None

    depth_score = band_score(groundwater_depth_m, depth_bands)
    area_score = band_score(available_area_m2, area_bands)
    if depth_score is None or area_score is None:
        return None, None
    total = float(soil["score"]) + depth_score + area_score
    for threshold in sorted(thresholds, key=lambda item: item["minimumScore"], reverse=True):
        if total >= threshold["minimumScore"]:
            return threshold["classification"], float(soil.get("rechargeFraction", 0))
    return None, None


def select_structure(
    classification: str | None,
    available_area_m2: float,
    rules: dict[str, Any],
) -> tuple[dict[str, str] | None, dict[str, Any] | None]:
    if classification is None:
        return None, None
    for rule in rules.get("structureRules", []):
        if (
            classification in rule["allowedClassifications"]
            and available_area_m2 >= rule["minimumAreaM2"]
        ):
            return (
                {"type": rule["type"], "displayName": rule["displayName"]},
                rule.get("dimensions"),
            )
    return None, None
