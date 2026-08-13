import json
from functools import lru_cache
from pathlib import Path

from .models import SourceCitation

SOURCE_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "sources.json"


@lru_cache
def source_registry() -> dict[str, SourceCitation]:
    with SOURCE_REGISTRY_PATH.open(encoding="utf-8") as source:
        payload = json.load(source)
    citations = [SourceCitation.model_validate(item) for item in payload["sources"]]
    registry = {citation.source_id: citation for citation in citations}
    if len(registry) != len(citations):
        raise RuntimeError("Source registry contains duplicate source IDs.")
    return registry


def citations_for(*source_ids: str) -> list[SourceCitation]:
    registry = source_registry()
    missing = [source_id for source_id in source_ids if source_id not in registry]
    if missing:
        raise RuntimeError(f"Unknown source IDs: {', '.join(missing)}")
    return [registry[source_id] for source_id in source_ids]
