from typing import Any


def normalize_location(value: str) -> str:
    return " ".join(value.casefold().replace(",", " ").split())


def get_rainfall(location: str, config: dict[str, Any]) -> dict[str, Any] | None:
    requested = normalize_location(location)
    for item in config.get("locations", []):
        names = [item["name"], *item.get("aliases", [])]
        if requested in {normalize_location(name) for name in names}:
            return item
    return config.get("default")
