-- Profile avatar picture stored in MinIO; this column holds the object key.
ALTER TABLE fixmymedtech.profiles
  ADD COLUMN IF NOT EXISTS avatar_key TEXT;