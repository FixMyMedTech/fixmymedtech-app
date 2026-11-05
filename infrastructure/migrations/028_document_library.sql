-- 028_document_library.sql
-- Document library: manuals and guides shared between devices, linked from
-- iFixit or uploaded to FixMyMedTech.
--
-- documents becomes the library itself. A row is either
--   source = 'ifixit'  a LINK to a document in the iFixit library (url plus
--                      its iFixit ids); the file is never copied here, or
--   source = 'upload'  a file uploaded to FixMyMedTech (storage_key in MinIO).
-- An iFixit document is stored once (unique ifixit_document_id) and shared by
-- every device that uses it.
--
-- device_documents links devices and documents (many to many). It replaces
-- documents.device_id; existing links are moved over before that column goes.
--
-- contribution_status tracks sending an UPLOAD to iFixit, which a platform
-- superuser approves first: pending → approved → sent, or rejected / failed.
-- NULL for iFixit documents.
--
-- Idempotent: safe to re-run.

CREATE TABLE IF NOT EXISTS fixmymedtech.device_documents (
  device_id   UUID NOT NULL REFERENCES fixmymedtech.devices(id) ON DELETE CASCADE,
  document_id UUID NOT NULL REFERENCES fixmymedtech.documents(id) ON DELETE CASCADE,
  added_by    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (device_id, document_id)
);
CREATE INDEX IF NOT EXISTS ix_device_documents_document ON fixmymedtech.device_documents (document_id);

ALTER TABLE fixmymedtech.documents
  ADD COLUMN IF NOT EXISTS source              TEXT NOT NULL DEFAULT 'upload',
  ADD COLUMN IF NOT EXISTS storage_key         TEXT,
  ADD COLUMN IF NOT EXISTS pages               INT,
  ADD COLUMN IF NOT EXISTS thumbnail_url       TEXT,
  ADD COLUMN IF NOT EXISTS manufacturer        TEXT,
  ADD COLUMN IF NOT EXISTS model               TEXT,
  ADD COLUMN IF NOT EXISTS ifixit_document_id  BIGINT,
  ADD COLUMN IF NOT EXISTS ifixit_guid         TEXT,
  ADD COLUMN IF NOT EXISTS ifixit_page         TEXT,
  ADD COLUMN IF NOT EXISTS uploaded_by         UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS contribution_status TEXT,
  ADD COLUMN IF NOT EXISTS contribution_error  TEXT,
  ADD COLUMN IF NOT EXISTS reviewed_by         UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS reviewed_at         TIMESTAMPTZ;

-- Uploaded files are served from storage, so they have no external url.
ALTER TABLE fixmymedtech.documents ALTER COLUMN url DROP NOT NULL;

-- Move existing device links into the link table, then drop the old column.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.columns
             WHERE table_schema = 'fixmymedtech' AND table_name = 'documents' AND column_name = 'device_id') THEN
    INSERT INTO fixmymedtech.device_documents (device_id, document_id)
      SELECT device_id, id FROM fixmymedtech.documents WHERE device_id IS NOT NULL
      ON CONFLICT DO NOTHING;
    ALTER TABLE fixmymedtech.documents DROP COLUMN device_id;
  END IF;
END $$;

-- New document types. Old values are mapped onto the new set first.
ALTER TABLE fixmymedtech.documents DROP CONSTRAINT IF EXISTS documents_type_check;
UPDATE fixmymedtech.documents SET type = CASE type
    WHEN 'manual'    THEN 'user_manual'
    WHEN 'checklist' THEN 'quick_guide'
    WHEN 'video'     THEN 'general_guide'
    ELSE type END
  WHERE type IN ('manual', 'checklist', 'video');
ALTER TABLE fixmymedtech.documents ADD CONSTRAINT documents_type_check
  CHECK (type IN ('user_manual', 'service_manual', 'quick_guide', 'diagram', 'general_guide'));

ALTER TABLE fixmymedtech.documents DROP CONSTRAINT IF EXISTS documents_source_check;
ALTER TABLE fixmymedtech.documents ADD CONSTRAINT documents_source_check
  CHECK (source IN ('ifixit', 'upload'));

ALTER TABLE fixmymedtech.documents DROP CONSTRAINT IF EXISTS documents_contribution_status_check;
ALTER TABLE fixmymedtech.documents ADD CONSTRAINT documents_contribution_status_check
  CHECK (contribution_status IS NULL OR contribution_status IN ('pending', 'approved', 'sent', 'rejected', 'failed'));

CREATE UNIQUE INDEX IF NOT EXISTS ux_documents_ifixit_document_id
  ON fixmymedtech.documents (ifixit_document_id) WHERE ifixit_document_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_documents_created_at ON fixmymedtech.documents (created_at DESC);
