from typing import Any


def recommended_storage_litres(
    potential_litres: float, rules: dict[str, Any]
) -> tuple[float | None, str | None]:
    fraction = rules.get("storageFractionOfAnnualPotential")
    increments = rules.get("roundUpToLitres")
    maximum = rules.get("maximumStorageLitres")
    if fraction is None or increments is None:
        return None, "Assessment unavailable. Engineering sizing rule not configured yet."
    raw_size = potential_litres * float(fraction)
    rounded = ((raw_size + increments - 1) // increments) * increments
    if maximum is not None:
        rounded = min(rounded, maximum)
    return float(rounded), None
