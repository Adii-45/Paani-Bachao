import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DESIGN_PATH = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "source_backed"
    / "delhi_recharge_standard_designs.json"
)


@lru_cache
def load_delhi_standard_designs() -> dict[str, Any]:
    with DESIGN_PATH.open(encoding="utf-8") as source:
        return json.load(source)


def normalize_formation(*values: str | None) -> str | None:
    text = " ".join(value for value in values if value).upper()
    if "ALLUVI" in text:
        return "ALLUVIAL"
    if any(token in text for token in ("HARD ROCK", "QUARTZITE", "GRANITE", "BASALT")):
        return "HARD_ROCK"
    return None


def design_row(structure_type: str, roof_area_m2: float) -> dict[str, float] | None:
    if roof_area_m2 <= 0:
        raise ValueError("Roof area must be greater than zero.")
    key = {
        "RECHARGE_TRENCH": "trenchWithoutWell",
        "TRENCH_WITH_RECHARGE_WELL": "trenchWithRechargeWell",
    }.get(structure_type)
    if key is None:
        return None
    for row in load_delhi_standard_designs()[key]:
        if roof_area_m2 <= row["maximumRoofAreaM2"]:
            return row
    return None
