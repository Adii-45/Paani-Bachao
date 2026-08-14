from dataclasses import dataclass


@dataclass(frozen=True)
class RainfallMM:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Rainfall cannot be negative.")


@dataclass(frozen=True)
class AreaSquareMeters:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Area cannot be negative.")


@dataclass(frozen=True)
class RunoffCoefficient:
    value: float

    def __post_init__(self) -> None:
        if not 0 <= self.value <= 1:
            raise ValueError("Runoff coefficient must be between 0 and 1.")


@dataclass(frozen=True)
class VolumeLitres:
    value: float

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("Volume cannot be negative.")
