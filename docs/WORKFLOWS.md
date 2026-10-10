# FarmShield — End-to-End Workflows

## Workflow 1: Authentication & Authorization
- Farmers and Administrators register or sign in via `/api/v1/auth/register` and `/api/v1/auth/login`.
- Passwords hashed using PBKDF2-HMAC-SHA256 with cryptographically random salts.
- Cryptographically signed JWT tokens issued with expiration.
- Multi-tenancy enforced: Farmers can only access their own storage batches, sensor readings, and diaries.

## Workflow 2: Crop Onboarding & Scientific Profile Association
- Farmer selects from 16 verified Indian crops loaded dynamically from MongoDB.
- Backend retrieves matching verified ICAR/FAO profile.
- Farmer specifies custom batch name, harvest date, storage structure, and quantity (kg).
- Storage batch is created and bound to the verified profile version.

## Workflow 3: Multi-Crop Storage Batches
- Farmers manage multiple concurrent batches (e.g. Paddy in a Pusa Bin and Onions in a Thatched Chawl).
- Active batch switcher in navbar updates live telemetry instantly.

## Workflow 4: Sensor & Manual Telemetry Ingestion
- Readings ingested via `/api/v1/batches/{batch_id}/readings`.
- Provenance tagged as `manual`, `hardware_sensor`, or `simulated`.
- Immediate validation against verified crop bounds.

## Workflow 5: Real-Time Monitoring Dashboard
- Live gauges display temperature and humidity with crop-specific safe range bars.
- Instant risk level indication (`normal`, `moderate`, `critical`).

## Workflow 6: Farmer Diary & Observation Log
- Observations categorized by inspection type (smell, insect activity, moisture leakage, caking, hotspot).
- Speech-to-text voice memos transcribed via Azure Speech.
- Provenance distinguishes visual inspection from sensor readings.

## Workflow 7 & 8: AI Advisory with Groq & RAG
- Farmer asks storage questions in natural language.
- Context builder injects verified limits, active readings, and traditional ITK knowledge.
- Groq generates actionable advice citing ICAR and traditional sources.

## Workflow 9: Weather Forecasts & Aeration Advisory
- Fetches atmospheric forecasts and provides aeration instructions (e.g., ventilate during dry afternoon, seal during humid morning).

## Workflow 10: APMC Mandi Market Prices
- Real modal wholesale mandi prices across APMCs.
- Storage vs selling economic holding guidance.

## Workflow 11: Alert Engine & WhatsApp Dispatch
- Threshold evaluation triggers warnings or critical alerts.
- Bounded notification attempts logged in `notification_logs`.
- Automatic resolution when conditions recover.

## Workflow 12: Multilingual Support
- Supports English, Hindi, Telugu, Tamil, Kannada, Marathi, Punjabi, Bengali.

## Workflow 13 & 14: Administrator Diagnostics
- System readiness diagnostics, integration API key status without exposing secrets, crop verification tools, and audit logs.
