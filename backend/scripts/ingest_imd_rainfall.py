"""Fetch or import IMD's official 1971-2020 annual and monthly normal layers."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

import httpx

from app.importers.imd_rainfall import (
    IMD_LAYER_URL,
    IMD_MONTHLY_LAYER_URLS,
    MONTH_CODES,
    IMDDistrictRainfallImporter,
)

DEFAULT_OUTPUT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "data"
    / "normalized"
    / "imd_normal_annual_rainfall.json.gz"
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-file", type=Path)
    parser.add_argument(
        "--monthly-source-directory",
        type=Path,
        help="Directory containing jan.js through dec.js from IMD",
    )
    parser.add_argument("--source-url", default=IMD_LAYER_URL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--confirm-official-source", action="store_true")
    args = parser.parse_args()
    if not args.confirm_official_source:
        parser.error("--confirm-official-source is required")

    if args.source_file:
        source_text = args.source_file.read_text(encoding="utf-8")
    else:
        response = httpx.get(
            args.source_url,
            follow_redirects=True,
            timeout=60,
            headers={"User-Agent": "Paani-Bachao rainfall importer"},
        )
        response.raise_for_status()
        source_text = response.text

    if args.monthly_source_directory:
        monthly_source_texts = {
            month: (args.monthly_source_directory / f"{month}.js").read_text(
                encoding="utf-8"
            )
            for month in MONTH_CODES
        }
    else:
        monthly_source_texts = {}
        for month in MONTH_CODES:
            response = httpx.get(
                IMD_MONTHLY_LAYER_URLS[month],
                follow_redirects=True,
                timeout=60,
                headers={"User-Agent": "Paani-Bachao rainfall importer"},
            )
            response.raise_for_status()
            monthly_source_texts[month] = response.text

    importer = IMDDistrictRainfallImporter()
    normalized = importer.normalize(
        source_text,
        imported_at=datetime.now(UTC),
        monthly_source_texts=monthly_source_texts,
    )
    importer.write(normalized, args.output)
    print(f"Imported {normalized['record_count']} IMD records into {args.output}")


if __name__ == "__main__":
    main()
