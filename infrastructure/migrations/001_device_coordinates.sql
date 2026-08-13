-- ============================================================
-- Migration 001: add device coordinates
-- Aligns the Supabase schema with the SQLAlchemy model
-- (latitude/longitude were present in db/init.sql but missing here).
-- ============================================================

ALTER TABLE fixmymedtech.devices
  ADD COLUMN IF NOT EXISTS latitude  DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
