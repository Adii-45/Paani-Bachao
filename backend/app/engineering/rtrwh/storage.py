from dataclasses import dataclass
from enum import Enum


class StorageSizingStatus(str, Enum):
    SIZE_AVAILABLE = "SIZE_AVAILABLE"
    INSUFFICIENT_DATA_FOR_SIZING = "INSUFFICIENT_DATA_FOR_SIZING"


@dataclass(frozen=True)
class StorageSizingResult:
    status: StorageSizingStatus
    recommended_litres: float | None
    method_id: str
    missing_inputs: tuple[str, ...]
    source_ids: tuple[str, ...]
    message: str


def assess_storage_size() -> StorageSizingResult:
    """Report why the current MVP inputs cannot support tank sizing.

    CGWB Manual (2007), §7.2.7.2 and §7.3.2 requires event rainfall or
    rainfall distribution for the described urban sizing approach. The API also
    lacks demand/allocation inputs for a demand-reliability strategy.
    """

    return StorageSizingResult(
        status=StorageSizingStatus.INSUFFICIENT_DATA_FOR_SIZING,
        recommended_litres=None,
        method_id="CGWB_MANUAL_2007_STORAGE_DATA_REQUIREMENTS",
        missing_inputs=(
            "event rainfall or rainfall distribution",
            "intended use and water allocation",
            "demand profile and design reliability (for demand-based sizing)",
        ),
        source_ids=("CGWB_MANUAL_AR_2007", "BIS_IS_15797_2008"),
        message=(
            "Storage capacity cannot be sized from annual harvesting potential alone. "
            "Event rainfall/distribution and the selected demand or use strategy are required."
        ),
    )
