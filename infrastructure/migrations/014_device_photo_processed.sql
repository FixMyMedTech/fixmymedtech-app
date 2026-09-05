-- 014_device_photo_processed.sql
-- Store the MinIO key of the white-background processed copy of a device
-- photo. The original is always kept in photo_key; the processed copy is
-- generated asynchronously after upload.

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS photo_processed_key TEXT;