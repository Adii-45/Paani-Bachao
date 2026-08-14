import json
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from ..domain.ar_environment import EnvironmentalResolution, GroundwaterObservation
from ..provenance.models import DataQuality, DataStatus, ValueProvenance
from ..provenance.registry import source_registry

OBSERVATION_SOURCE_ID = "CGWB_GWL_NOVEMBER_2022"
STATION_SOURCE_ID = "CGWB_WQ_2020_STATION_COORDINATES"
SUPPORTED_DATASET_STATUSES = {DataStatus.DATA_AVAILABLE, DataStatus.DATA_STALE}


def _value(row: Mapping[str, Any], *names: str) -> Any:
    for name in names:
        value = row.get(name)
        if value is not None and str(value).strip():
            return value
    return None


def _required(row: Mapping[str, Any], *names: str) -> Any:
    value = _value(row, *names)
    if value is None:
        raise ValueError(f"Groundwater source row is missing required field: {names[0]}.")
    return value


def _parse_date(value: Any) -> date:
    text = str(value).strip()
    for pattern in (None, "%d-%b-%Y", "%d/%m/%Y"):
        try:
            return date.fromisoformat(text) if pattern is None else datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    raise ValueError(f"Unsupported groundwater observation date: {text}.")


def _depth_metres(value: Any, unit: Any) -> float:
    normalized_unit = " ".join(str(unit).strip().casefold().replace(".", "").split())
    metre_units = {
        "m",
        "meter",
        "meters",
        "metre",
        "metres",
        "m bgl",
        "mbgl",
        "meter bgl",
        "meters bgl",
        "metre bgl",
        "metres bgl",
        "metres below ground level",
        "meters below ground level",
    }
    if normalized_unit not in metre_units:
        raise ValueError(
            f"Unsupported groundwater depth unit: {unit}. Expected metres below ground level."
        )
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Groundwater depth is not numeric.") from exc


def _normalized_admin(value: Any) -> str:
    return "".join(character for character in str(value).casefold() if character.isalnum())


class CGWBGroundwaterImporter:
    """Join reviewed CGWB water-level rows to official station coordinates."""

    def normalize(
        self,
        observation_rows: Iterable[Mapping[str, Any]],
        station_rows: Iterable[Mapping[str, Any]],
        *,
        imported_at: datetime,
        dataset_status: DataStatus,
        dataset_version: str,
    ) -> dict[str, Any]:
        registry = source_registry()
        for source_id in (OBSERVATION_SOURCE_ID, STATION_SOURCE_ID):
            if source_id not in registry:
                raise ValueError(f"Unknown source ID: {source_id}")
        if dataset_status not in SUPPORTED_DATASET_STATUSES:
            raise ValueError("Groundwater dataset status must be DATA_AVAILABLE or DATA_STALE.")
        if not dataset_version.strip():
            raise ValueError("Groundwater dataset version is required.")
        if imported_at.tzinfo is None:
            raise ValueError("Groundwater import timestamp must include a timezone.")

        stations: dict[str, Mapping[str, Any]] = {}
        for row in station_rows:
            station_id = str(_required(row, "stationId", "station_id")).strip()
            if station_id in stations:
                raise ValueError(f"Duplicate groundwater station ID: {station_id}.")
            # Validate coordinates before accepting the station into the join.
            latitude = float(_required(row, "latitude"))
            longitude = float(_required(row, "longitude"))
            if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
                raise ValueError(f"Invalid coordinates for groundwater station {station_id}.")
            stations[station_id] = row

        records: list[GroundwaterObservation] = []
        seen_observations: set[tuple[str, date, str]] = set()
        for row in observation_rows:
            station_id = str(_required(row, "stationId", "station_id")).strip()
            station = stations.get(station_id)
            if station is None:
                raise ValueError(
                    f"Groundwater station {station_id} has no reviewed coordinate record."
                )
            observation_date = _parse_date(
                _required(row, "observationDate", "observation_date")
            )
            season = str(_required(row, "season")).strip()
            identity = (station_id, observation_date, season.casefold())
            if identity in seen_observations:
                raise ValueError(
                    f"Duplicate groundwater observation for {station_id} on {observation_date}."
                )
            seen_observations.add(identity)

            depth = _depth_metres(
                _required(row, "depthBelowGroundLevel", "depth_below_ground_level"),
                _required(row, "depthUnit", "depth_unit"),
            )
            district = str(
                _required(row, "district")
                if _value(row, "district") is not None
                else _required(station, "district")
            ).strip()
            state = str(
                _required(row, "state")
                if _value(row, "state") is not None
                else _required(station, "state")
            ).strip()
            for field, selected in (("district", district), ("state", state)):
                station_value = _value(station, field)
                if station_value and _normalized_admin(station_value) != _normalized_admin(selected):
                    raise ValueError(
                        f"Groundwater {field} differs between observation and station "
                        f"records for {station_id}."
                    )

            station_name = str(
                _value(row, "stationName", "station_name")
                or _required(station, "stationName", "station_name")
            ).strip()
            record = GroundwaterObservation(
                stationId=station_id,
                stationName=station_name,
                stationType=_value(row, "stationType", "station_type")
                or _value(station, "stationType", "station_type"),
                aquiferNature=_value(row, "aquiferNature", "aquifer_nature")
                or _value(station, "aquiferNature", "aquifer_nature"),
                depthBelowGroundLevelM=depth,
                depthUnit="m bgl",
                observationDate=observation_date,
                season=season,
                latitude=float(_required(station, "latitude")),
                longitude=float(_required(station, "longitude")),
                district=district,
                state=state,
                spatialResolution=EnvironmentalResolution.NEARBY_OBSERVATION,
                provenance=ValueProvenance(
                    quality=DataQuality.AUTHORITATIVE_DATASET,
                    sourceIds=[OBSERVATION_SOURCE_ID, STATION_SOURCE_ID],
                    sourceRecord=(
                        f"Station {station_id}, {station_name}; observation "
                        f"{observation_date.isoformat()} joined to official station coordinates"
                    ),
                    sourceDateOrVersion=dataset_version,
                    spatialResolution=(
                        "CGWB monitoring-well point at the coordinates published in the "
                        "reviewed station source"
                    ),
                    temporalResolution=f"single observation; season={season}",
                    retrievedAt=imported_at.astimezone(UTC),
                    notes=(
                        "Station observation, not groundwater depth directly beneath the property."
                    ),
                ),
            )
            records.append(record)

        if not records:
            raise ValueError("Groundwater import contains no observations.")
        records.sort(
            key=lambda item: (
                item.state.casefold(),
                item.district.casefold(),
                item.station_id,
                item.observation_date,
                item.season.casefold(),
            )
        )
        return {
            "datasetStatus": dataset_status.value,
            "datasetVersion": dataset_version,
            "importedAt": imported_at.astimezone(UTC).isoformat(),
            "sourceIds": [OBSERVATION_SOURCE_ID, STATION_SOURCE_ID],
            "recordCount": len(records),
            "refreshStrategy": (
                "Import the next reviewed CGWB/India-WRIS seasonal observation export "
                "and matching official station-coordinate export."
            ),
            "records": [
                record.model_dump(mode="json", by_alias=True) for record in records
            ],
        }

    @staticmethod
    def write(normalized: dict[str, Any], output_path: Path) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(normalized, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
