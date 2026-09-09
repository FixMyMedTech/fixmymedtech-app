-- 017_fault_report_photo.sql
-- Store the MinIO object key of a photo attached to a fault report. The image
-- is uploaded as-is (no background processing, unlike device photos).

ALTER TABLE fixmymedtech.fault_reports
  ADD COLUMN IF NOT EXISTS photo_key TEXT;