-- 013_device_photo.sql
-- Store the MinIO object key of a device photo on the devices row.

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS photo_key TEXT;