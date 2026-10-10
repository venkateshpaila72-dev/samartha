# FarmShield — Database Seeding & Data Validation Guide

## 1. Overview
The FarmShield database is pre-seeded with 16 scientifically verified Indian crop storage profiles and traditional storage techniques. The crop collection is never left empty.

## 2. Seed Data Validation
Run the standalone data validator to ensure numeric constraints, temperature bounds, humidity percentages, and source citations:

```bash
cd backend
python scripts/validate_crop_data.py
```

Expected output:
```text
SUCCESS: All 16 crop storage profiles passed validation successfully!
Unique Verified Crops Seeded: 16
  - Paddy (Rice) (paddy_grain_ambient) -> Temp: 15.0-25.0°C, RH: 55.0-68.0%, Moisture: 13.0% [verified]
  - Wheat (wheat_grain_ambient) -> Temp: 15.0-22.0°C, RH: 50.0-65.0%, Moisture: 11.5% [verified]
  ...
```

## 3. Database Seeding
To seed records into live MongoDB:

```bash
cd backend
python -m scripts.seed_crop_storage_profiles
```

To update records while overwriting administrator customizations:

```bash
python -m scripts.seed_crop_storage_profiles --overwrite
```

## 4. Automatic Seeding Fallback
If the live MongoDB database is starting for the first time or operating in test mode, FarmShield automatically loads the validated dataset directly from `backend/data/crop_storage_profiles.json` upon startup so that crop selection and telemetry rules function immediately.
