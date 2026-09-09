-- 009_add_registered_by.sql
-- Add registered_by column to devices table

ALTER TABLE fixmymedtech.devices
    ADD COLUMN IF NOT EXISTS registered_by UUID REFERENCES fixmymedtech.profiles(id);
