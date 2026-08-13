import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA_ROOT = Path(__file__).resolve().parent.parent / "data"


def active_ruleset() -> str:
    value = os.getenv("RAINASSESS_RULESET", "demo").lower()
    if value not in {"demo", "production"}:
        raise RuntimeError("RAINASSESS_RULESET must be 'demo' or 'production'.")
    return value


@lru_cache
def load_rule(name: str, ruleset: str | None = None) -> dict[str, Any]:
    selected = ruleset or active_ruleset()
    path = DATA_ROOT / selected / f"{name}.json"
    if not path.is_file():
        raise RuntimeError(f"Rule configuration is missing: {path.name}")
    with path.open(encoding="utf-8") as source:
        return json.load(source)
