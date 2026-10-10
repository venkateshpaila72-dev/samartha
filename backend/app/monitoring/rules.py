"""Monitoring Rules and Threshold Evaluator for FarmShield."""

from typing import Optional


class EvaluationResult:
    def __init__(
        self,
        condition_type: str,
        is_triggered: bool,
        severity: str,
        measured_value: float,
        target_threshold: float,
        unit: str,
        message: str,
        recommended_action: str,
    ):
        self.condition_type = condition_type
        self.is_triggered = is_triggered
        self.severity = severity
        self.measured_value = measured_value
        self.target_threshold = target_threshold
        self.unit = unit
        self.message = message
        self.recommended_action = recommended_action


def evaluate_measurement_rules(
    temp_c: float,
    humidity_pct: float,
    moisture_pct: Optional[float],
    crop_profile: dict,
) -> list[EvaluationResult]:
    results = []

    t_min = crop_profile.get("recommended_temperature_min_c", 15.0)
    t_max = crop_profile.get("recommended_temperature_max_c", 25.0)
    rh_min = crop_profile.get("recommended_relative_humidity_min_percent", 50.0)
    rh_max = crop_profile.get("recommended_relative_humidity_max_percent", 70.0)
    safe_moisture = crop_profile.get("recommended_crop_moisture_percent", 12.0)
    crop_name = crop_profile.get("crop_name", "Crop")

    # 1. Temperature High Rule
    if temp_c > t_max:
        is_crit = (temp_c - t_max) >= 4.0
        results.append(
            EvaluationResult(
                condition_type="temperature_high",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=temp_c,
                target_threshold=t_max,
                unit="°C",
                message=f"Storage temperature for {crop_name} is {temp_c:.1f}°C, exceeding maximum safe limit of {t_max:.1f}°C.",
                recommended_action=f"Activate ventilation or exhaust fans immediately during cooler hours. Check for internal hotspot heating.",
            )
        )

    # 2. Temperature Low Rule
    elif temp_c < t_min:
        is_crit = (t_min - temp_c) >= 5.0
        results.append(
            EvaluationResult(
                condition_type="temperature_low",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=temp_c,
                target_threshold=t_min,
                unit="°C",
                message=f"Storage temperature for {crop_name} is {temp_c:.1f}°C, below minimum recommended limit of {t_min:.1f}°C.",
                recommended_action="Ensure storage room insulation and protect from frost/chilling injury.",
            )
        )

    # 3. Humidity High Rule
    if humidity_pct > rh_max:
        is_crit = (humidity_pct - rh_max) >= 8.0
        results.append(
            EvaluationResult(
                condition_type="humidity_high",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=humidity_pct,
                target_threshold=rh_max,
                unit="%",
                message=f"Relative humidity is {humidity_pct:.1f}%, exceeding safe maximum of {rh_max:.1f}% for {crop_name}.",
                recommended_action="High humidity accelerates mold/fungal sporulation. Increase aeration or use moisture absorbent/lime cushions.",
            )
        )

    # 4. Humidity Low Rule
    elif humidity_pct < rh_min:
        results.append(
            EvaluationResult(
                condition_type="humidity_low",
                is_triggered=True,
                severity="warning",
                measured_value=humidity_pct,
                target_threshold=rh_min,
                unit="%",
                message=f"Relative humidity is {humidity_pct:.1f}%, below minimum target of {rh_min:.1f}%.",
                recommended_action="Low humidity may cause shrinkage and dehydration in fresh produce.",
            )
        )

    # 5. Moisture High Rule (if moisture measurement is provided)
    if moisture_pct is not None and moisture_pct > safe_moisture:
        is_crit = (moisture_pct - safe_moisture) >= 1.5
        results.append(
            EvaluationResult(
                condition_type="moisture_high",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=moisture_pct,
                target_threshold=safe_moisture,
                unit="%",
                message=f"Crop grain moisture is {moisture_pct:.1f}%, exceeding safe storage limit of {safe_moisture:.1f}%.",
                recommended_action="Unload grain immediately and sun-dry in thin layers on clean tarpaulins before re-bagging.",
            )
        )

    return results
