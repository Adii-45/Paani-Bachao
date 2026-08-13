def calculate_potential_litres(
    roof_area_m2: float, annual_rainfall_mm: float, runoff_coefficient: float
) -> float:
    """1 mm of rain over 1 m² equals 1 litre of water."""
    return round(roof_area_m2 * annual_rainfall_mm * runoff_coefficient, 2)
