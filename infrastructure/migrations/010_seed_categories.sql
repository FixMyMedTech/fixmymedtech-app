-- 010_seed_categories.sql
-- Ensure all guide categories + Other exist in device_categories
-- Fix column default first, then insert with explicit UUIDs

ALTER TABLE fixmymedtech.device_categories
    ALTER COLUMN id SET DEFAULT gen_random_uuid();

INSERT INTO fixmymedtech.device_categories (id, name, icon, slug) VALUES
  (gen_random_uuid(), 'Anaesthetic Machines', '⛽', 'anaesthetic_machine'),
  (gen_random_uuid(), 'Autoclaves and Sterilizers', '🧪', 'autoclave_sterilizer'),
  (gen_random_uuid(), 'ECG (Electrocardiograph) Machines', '💓', 'ecg_machine'),
  (gen_random_uuid(), 'Electronic Diagnostic Equipment', '🔍', 'electronic_diagnostic_equipment'),
  (gen_random_uuid(), 'Electrosurgical Units (ESU) and Cautery Machines', '🔥', 'electrosurgical_unit'),
  (gen_random_uuid(), 'Endoscopes', '🔭', 'endoscope'),
  (gen_random_uuid(), 'Incubators (Infant)', '👶', 'infant_incubator'),
  (gen_random_uuid(), 'Lamps', '💡', 'lamp'),
  (gen_random_uuid(), 'Nebulizers', '🌫️', 'nebulizer'),
  (gen_random_uuid(), 'Oxygen Concentrators', '🫧', 'oxygen_concentrator'),
  (gen_random_uuid(), 'Oxygen Cylinders and Flowmeters', '💨', 'oxygen_cylinder_flowmeter'),
  (gen_random_uuid(), 'Pulse Oximeters', '🖐️', 'pulse_oximeter'),
  (gen_random_uuid(), 'Scales', '⚖️', 'scale'),
  (gen_random_uuid(), 'Sphygmomanometers (B.P. sets)', '🩸', 'sphygmomanometer'),
  (gen_random_uuid(), 'Stethoscopes', '🩺', 'stethoscope'),
  (gen_random_uuid(), 'Suction Machines', '🌀', 'suction_machine'),
  (gen_random_uuid(), 'Operating Theatre and Delivery Tables', '🛏️', 'operating_table'),
  (gen_random_uuid(), 'Ultrasound Machines', '📡', 'ultrasound_machine'),
  (gen_random_uuid(), 'X-Ray Machines', '🔬', 'xray_machine'),
  (gen_random_uuid(), 'Other', '🏥', 'other')
ON CONFLICT (slug) DO NOTHING;
