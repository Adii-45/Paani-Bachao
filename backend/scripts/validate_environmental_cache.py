"""Report whether normalized environmental caches are provider-ready."""

import argparse
from datetime import UTC, datetime
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.domain.environmental_validation import (  # noqa: E402
    CacheValidationStatus,
    EnvironmentalCacheReport,
    EnvironmentalDataset,
)
from app.services.environmental_validation import (  # noqa: E402
    DEFAULT_CACHE_PATHS,
    EnvironmentalCacheValidator,
)


def validate_cache(path: Path, dataset_type: str) -> int:
    """Backward-compatible strict schema/provenance check used by existing tests."""

    dataset = EnvironmentalDataset(dataset_type)
    report = EnvironmentalCacheValidator(paths={dataset: path}).validate(dataset)
    if report.status in {
        CacheValidationStatus.MISSING,
        CacheValidationStatus.MALFORMED,
        CacheValidationStatus.PARTIAL,
        CacheValidationStatus.UNSUPPORTED_METADATA,
    }:
        raise ValueError("; ".join(report.issues) or report.status.value)
    return report.valid_record_count


def _print_report(report: EnvironmentalCacheReport) -> None:
    print(report.dataset.value.upper())
    print(report.status.value)
    print(f"provider status: {report.provider_status.value}")
    print(f"usable: {'yes' if report.usable else 'no'}")
    print(
        f"records: {report.valid_record_count}/{report.record_count} valid"
        + (
            f", {report.invalid_record_count} invalid"
            if report.invalid_record_count
            else ""
        )
    )
    print(f"source IDs: {', '.join(report.source_ids) or 'unavailable'}")
    print(f"version: {report.dataset_version or 'unavailable'}")
    print(
        "imported: "
        + (report.imported_at.isoformat() if report.imported_at else "unavailable")
    )
    if report.observation_period:
        print(f"observation period: {report.observation_period}")
    if report.latest_observation_date:
        print(f"latest observation: {report.latest_observation_date.isoformat()}")
    if report.coverage and report.coverage.bounding_box:
        print(f"coverage bounding box: {report.coverage.bounding_box}")
    if report.component_counts:
        components = ", ".join(
            f"{name}={count}" for name, count in report.component_counts.items()
        )
        print(f"components: {components}")
    for issue in report.issues:
        print(f"issue: {issue}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", choices=[item.value for item in EnvironmentalDataset])
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--all", action="store_true", dest="validate_all")
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args()
    if args.validate_all and (args.dataset or args.path):
        parser.error("--all cannot be combined with a dataset or path")
    if args.path and not args.dataset:
        parser.error("a custom path requires a dataset")

    validator = EnvironmentalCacheValidator(
        paths=(
            {EnvironmentalDataset(args.dataset): args.path}
            if args.dataset and args.path
            else DEFAULT_CACHE_PATHS
        ),
        as_of=datetime.now(UTC),
    )
    if args.dataset:
        report = validator.validate(EnvironmentalDataset(args.dataset))
        if args.json_output:
            print(report.model_dump_json(by_alias=True, indent=2))
        else:
            _print_report(report)
        raise SystemExit(0 if report.usable else 1)

    summary = validator.validate_all()
    if args.json_output:
        print(summary.model_dump_json(by_alias=True, indent=2))
    else:
        for report in summary.reports:
            _print_report(report)
        print(f"ALL DATASETS USABLE: {'YES' if summary.all_usable else 'NO'}")
    raise SystemExit(0 if summary.all_usable else 1)


if __name__ == "__main__":
    main()
