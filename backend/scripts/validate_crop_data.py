"""Validation script for FarmShield crop storage profiles.

Verifies structural integrity, numeric bounds, and scientific provenance
before database ingestion.
"""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = [
    "crop_id",
    "crop_name",
    "crop_category",
    "variety",
    "crop_form",
    "region",
    "storage_type",
    "intended_storage_duration",
    "recommended_temperature_min_c",
    "recommended_temperature_max_c",
    "recommended_relative_humidity_min_percent",
    "recommended_relative_humidity_max_percent",
    "recommended_crop_moisture_percent",
    "moisture_basis",
    "traditional_storage_methods",
    "ventilation_guidance",
    "pest_prevention_guidance",
    "spoilage_warning_signs",
    "recommended_actions",
    "source_name",
    "verification_status",
    "version",
    "is_active",
]


def validate_profile(profile: dict, index: int) -> list[str]:
    errors = []
    crop_id = profile.get("crop_id", f"item_{index}")

    for field in REQUIRED_FIELDS:
        if field not in profile or profile[field] is None:
            errors.append(f"[{crop_id}] Missing required field: '{field}'")

    temp_min = profile.get("recommended_temperature_min_c")
    temp_max = profile.get("recommended_temperature_max_c")
    if isinstance(temp_min, (int, float)) and isinstance(temp_max, (int, float)):
        if temp_min > temp_max:
            errors.append(f"[{crop_id}] Temperature min ({temp_min}°C) > max ({temp_max}°C)")
        if temp_min < -10 or temp_max > 60:
            errors.append(f"[{crop_id}] Temperature range [{temp_min}, {temp_max}] outside plausible bounds")
    else:
        errors.append(f"[{crop_id}] Temperature min/max must be numeric")

    rh_min = profile.get("recommended_relative_humidity_min_percent")
    rh_max = profile.get("recommended_relative_humidity_max_percent")
    if isinstance(rh_min, (int, float)) and isinstance(rh_max, (int, float)):
        if rh_min < 0 or rh_max > 100:
            errors.append(f"[{crop_id}] Relative humidity must be between 0 and 100%")
        if rh_min > rh_max:
            errors.append(f"[{crop_id}] RH min ({rh_min}%) > max ({rh_max}%)")
    else:
        errors.append(f"[{crop_id}] RH min/max must be numeric")

    moisture = profile.get("recommended_crop_moisture_percent")
    if not isinstance(moisture, (int, float)) or moisture <= 0 or moisture > 100:
        errors.append(f"[{crop_id}] Invalid recommended_crop_moisture_percent: {moisture}")

    trad_methods = profile.get("traditional_storage_methods")
    if not isinstance(trad_methods, list) or len(trad_methods) == 0:
        errors.append(f"[{crop_id}] traditional_storage_methods must be a non-empty list")

    source_name = profile.get("source_name")
    if not source_name or len(str(source_name).strip()) < 5:
        errors.append(f"[{crop_id}] source_name must specify a credible source citation")

    status = profile.get("verification_status")
    if status not in ["verified", "unverified", "pending_review"]:
        errors.append(f"[{crop_id}] Invalid verification_status: '{status}'")

    return errors


def main() -> int:
    base_dir = Path(__file__).resolve().parent.parent
    data_file = base_dir / "data" / "crop_storage_profiles.json"

    if not data_file.exists():
        print(f"ERROR: File not found: {data_file}")
        return 1

    try:
        with open(data_file, "r", encoding="utf-8") as f:
            profiles = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse JSON: {e}")
        return 1

    if not isinstance(profiles, list):
        print("ERROR: Root JSON element must be a list of crop profiles")
        return 1

    print(f"Validating {len(profiles)} crop profiles from {data_file}...")
    all_errors = []
    seen_ids = set()

    for idx, profile in enumerate(profiles):
        crop_id = profile.get("crop_id")
        if crop_id in seen_ids:
            all_errors.append(f"Duplicate crop_id detected: '{crop_id}'")
        if crop_id:
            seen_ids.add(crop_id)

        errs = validate_profile(profile, idx)
        all_errors.extend(errs)

    if all_errors:
        print(f"\nFAILED: Found {len(all_errors)} validation errors:")
        for err in all_errors:
            print(f"  - {err}")
        return 1

    print(f"SUCCESS: All {len(profiles)} crop storage profiles passed validation successfully!")
    print(f"Unique Verified Crops Seeded: {len(seen_ids)}")
    for p in profiles:
        print(f"  - {p['crop_name']} ({p['crop_id']}) -> Temp: {p['recommended_temperature_min_c']}-{p['recommended_temperature_max_c']}°C, RH: {p['recommended_relative_humidity_min_percent']}-{p['recommended_relative_humidity_max_percent']}%, Moisture: {p['recommended_crop_moisture_percent']}% [{p['verification_status']}]")

    return 0


if __name__ == "__main__":
    sys.exit(main())
