# FarmShield — Database Schema & Indexes

## Collections

### 1. `users`
- `id` (string, unique)
- `email` (string, unique index)
- `password_hash` (salt:iterations:key)
- `full_name` (string)
- `role` (string: `farmer`, `admin`, index)
- `preferred_language` (string: `en`, `hi`, `te`, etc.)
- `phone_number` (string)
- `village_or_location` (string)
- `created_at` (UTC ISO timestamp)

### 2. `crop_storage_profiles`
- `crop_id` (string, unique index)
- `crop_name` (string, index)
- `crop_category` (string, index)
- `variety` (string)
- `crop_form` (string)
- `region` (string)
- `storage_type` (string)
- `intended_storage_duration` (string)
- `recommended_temperature_min_c` (float)
- `recommended_temperature_max_c` (float)
- `recommended_relative_humidity_min_percent` (float)
- `recommended_relative_humidity_max_percent` (float)
- `recommended_crop_moisture_percent` (float)
- `moisture_basis` (string)
- `traditional_storage_methods` (list of strings)
- `ventilation_guidance` (string)
- `pest_prevention_guidance` (string)
- `spoilage_warning_signs` (list of strings)
- `recommended_actions` (list of strings)
- `source_name` (string)
- `verification_status` (string: `verified`, `unverified`)
- `version` (int)
- `is_active` (bool, index)

### 3. `storage_batches`
- `batch_id` (string, unique index)
- `farmer_id` (string, index)
- `crop_id` (string, index)
- `custom_batch_name` (string)
- `quantity_kg` (float)
- `harvest_date` (string)
- `storage_start_date` (string)
- `storage_structure_type` (string)
- `storage_location` (string)
- `status` (string: `active`, `closed`, compound index `[farmer_id, status]`)
- `latest_reading` (embedded document)

### 4. `sensor_readings`
- `reading_id` (string)
- `batch_id` (string, compound index `[batch_id, timestamp DESC]`)
- `temperature_c` (float)
- `relative_humidity_percent` (float)
- `crop_moisture_percent` (optional float)
- `sensor_id` (string, index)
- `provenance` (string: `manual`, `hardware_sensor`, `simulated`)
- `timestamp` (UTC ISO string)

### 5. `farmer_diary_entries`
- `entry_id` (string)
- `batch_id` (string, compound index `[batch_id, created_at DESC]`)
- `farmer_id` (string, index)
- `observation_text` (string)
- `observation_category` (string)
- `severity_assessment` (string)
- `provenance` (string)
- `photo_urls` (list of strings)
- `created_at` (UTC ISO string)

### 6. `storage_alerts`
- `alert_id` (string)
- `batch_id` (string, compound index `[batch_id, status]`)
- `condition_type` (string)
- `severity` (string: `warning`, `critical`, index)
- `measured_value` (float)
- `target_threshold` (float)
- `unit` (string)
- `message` (string)
- `recommended_action` (string)
- `status` (string: `active`, `acknowledged`, `resolved`)
- `whatsapp_notified` (bool)
- `created_at` (UTC ISO string, index)
- `resolved_at` (optional UTC ISO string)

### 7. `assistant_conversations` & `assistant_messages`
- Stored under compound indexes `[user_id]`, `[batch_id]`, and `[conversation_id, timestamp ASC]`.

### 8. `notification_logs` & `audit_logs`
- Delivery attempt logs with masked numbers and delivery status.
