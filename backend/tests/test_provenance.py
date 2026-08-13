import json

from app.provenance.registry import SOURCE_REGISTRY_PATH, source_registry


def test_source_registry_is_machine_readable_and_complete() -> None:
    payload = json.loads(SOURCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    registry = source_registry()

    assert len(registry) == len(payload["sources"])
    assert "CGWB_MANUAL_AR_2007" in registry
    for source in registry.values():
        assert source.authority
        assert source.document_title
        assert source.document_version_or_year
        assert source.source_url.startswith("https://")
        assert source.accessed_at.isoformat() == "2026-08-13"


def test_bis_status_is_recorded_without_encoding_unreviewed_clauses() -> None:
    source = source_registry()["BIS_IS_15797_2008"]

    assert "reaffirmed January 2023" in source.document_version_or_year
    assert source.section is None
    assert "not encoded" in (source.notes or "")
