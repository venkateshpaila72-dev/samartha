import re
from typing import Optional

E164_REGEX = r"^\+[1-9]\d{7,14}$"


def normalize_phone_number(raw_phone: Optional[str]) -> Optional[str]:
    """Normalizes phone number to strict E.164 standard (+[country_code][number])."""
    if not raw_phone or not isinstance(raw_phone, str):
        return None
    cleaned = raw_phone.strip()
    if cleaned.startswith("whatsapp:"):
        cleaned = cleaned.replace("whatsapp:", "").strip()
    # Strip spaces, hyphens, parens, dots
    cleaned = re.sub(r"[\s\-\(\)\.]", "", cleaned)
    if not cleaned:
        return None

    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    elif cleaned.startswith("+"):
        pass
    elif len(cleaned) == 10 and cleaned.isdigit():
        # Standard Indian mobile number default
        cleaned = f"+91{cleaned}"
    elif len(cleaned) == 11 and cleaned.startswith("0") and cleaned[1:].isdigit():
        cleaned = f"+91{cleaned[1:]}"
    elif len(cleaned) == 12 and cleaned.startswith("91") and cleaned.isdigit():
        cleaned = f"+{cleaned}"
    else:
        # Fallback with leading + if entirely digits
        if cleaned.isdigit():
            cleaned = f"+{cleaned}"

    if re.match(E164_REGEX, cleaned):
        return cleaned
    return None


def mask_phone_number(phone: Optional[str]) -> str:
    """Masks phone number for secure display in dashboards and logs."""
    if not phone:
        return "Not provided"
    norm = normalize_phone_number(phone) or phone
    if len(norm) <= 5:
        return "****"
    if norm.startswith("+91") and len(norm) == 13:
        # +91 7386****06
        return f"{norm[:7]}****{norm[-2:]}"
    return f"{norm[:4]}****{norm[-2:]}"


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
        target_min: Optional[float] = None,
        target_max: Optional[float] = None,
    ):
        self.condition_type = condition_type
        self.is_triggered = is_triggered
        self.severity = severity
        self.measured_value = measured_value
        self.target_threshold = target_threshold
        self.unit = unit
        self.message = message
        self.recommended_action = recommended_action
        self.target_min = target_min
        self.target_max = target_max


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
        rec = "Activate ventilation or exhaust fans immediately during cooler hours. Check for internal hotspot heating."
        if crop_profile.get("ventilation_guidance"):
            rec = f"{rec} {crop_profile.get('ventilation_guidance')}"
        results.append(
            EvaluationResult(
                condition_type="temperature_high",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=temp_c,
                target_threshold=t_max,
                unit="°C",
                message=f"Storage temperature for {crop_name} is {temp_c:.1f}°C, exceeding maximum safe limit of {t_max:.1f}°C (safe range: {t_min:.1f}°C–{t_max:.1f}°C).",
                recommended_action=rec,
                target_min=t_min,
                target_max=t_max,
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
                message=f"Storage temperature for {crop_name} is {temp_c:.1f}°C, below minimum recommended limit of {t_min:.1f}°C (safe range: {t_min:.1f}°C–{t_max:.1f}°C).",
                recommended_action="Ensure storage room insulation and protect from frost/chilling injury.",
                target_min=t_min,
                target_max=t_max,
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
                message=f"Relative humidity is {humidity_pct:.1f}%, exceeding safe maximum of {rh_max:.1f}% for {crop_name} (safe range: {rh_min:.1f}%–{rh_max:.1f}%).",
                recommended_action="High humidity accelerates mold/fungal sporulation. Increase aeration or use moisture absorbent/lime cushions.",
                target_min=rh_min,
                target_max=rh_max,
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
                message=f"Relative humidity is {humidity_pct:.1f}%, below minimum target of {rh_min:.1f}% (safe range: {rh_min:.1f}%–{rh_max:.1f}%).",
                recommended_action="Low humidity may cause shrinkage and dehydration in fresh produce.",
                target_min=rh_min,
                target_max=rh_max,
            )
        )

    # 5. Moisture High Rule (if moisture measurement is provided)
    if moisture_pct is not None and moisture_pct > safe_moisture:
        is_crit = (moisture_pct - safe_moisture) >= 1.5
        rec_actions = crop_profile.get("recommended_actions") or []
        rec = rec_actions[0] if rec_actions else "Unload grain immediately and sun-dry in thin layers on clean tarpaulins before re-bagging."
        results.append(
            EvaluationResult(
                condition_type="moisture_high",
                is_triggered=True,
                severity="critical" if is_crit else "warning",
                measured_value=moisture_pct,
                target_threshold=safe_moisture,
                unit="%",
                message=f"Crop grain moisture is {moisture_pct:.1f}%, exceeding safe storage limit of {safe_moisture:.1f}% for {crop_name}.",
                recommended_action=rec,
                target_min=None,
                target_max=safe_moisture,
            )
        )

    return results
