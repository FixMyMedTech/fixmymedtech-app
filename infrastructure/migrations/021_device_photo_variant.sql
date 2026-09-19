-- 021_device_photo_variant.sql
-- Which device photo should be shown on the public device page.

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS photo_public_variant TEXT NOT NULL DEFAULT 'processed';
