-- 029_community_roles.sql
-- Community journey, phase 1: community roles (the skill tree), the joining
-- flow and the community admin dashboard.
--
-- Community roles are NOT org roles. org_users.role (admin, technician, …)
-- decides what someone can do inside one organization. Community roles
-- (Ambassador, Mapper, Repairer, City lead…) are what a member is in the
-- community; they bring community permissions. Docs: docs/docs/community-journey.md
--
--   community_roles               the catalogue (the tree is data)
--   community_role_requirements   what unlocks each role (all rows must be met)
--   community_role_permissions    which permission keys each role grants
--   member_roles                  who holds which role, where
--   member_quests                 one-off steps the app can't read elsewhere
--   community_applications        the /join answers and the welcome meeting
--   community_role_changes        append-only log, shown in the History tab
--
-- New profile columns: member_status (applicant → member; staff for invited
-- clinic staff; refused), join_path, city, story fields, consent, activity.
--
-- Backfill: every profile that exists before this migration becomes a member
-- with the Ambassador role, so nobody already on the platform loses access.
--
-- Idempotent: safe to re-run.

-- ── Profiles ────────────────────────────────────────────────

ALTER TABLE fixmymedtech.profiles
  ADD COLUMN IF NOT EXISTS city                TEXT,
  ADD COLUMN IF NOT EXISTS country_trained     TEXT,
  ADD COLUMN IF NOT EXISTS why_bme             TEXT,
  ADD COLUMN IF NOT EXISTS member_status       TEXT,
  ADD COLUMN IF NOT EXISTS join_path           TEXT NOT NULL DEFAULT 'community',
  ADD COLUMN IF NOT EXISTS member_since        TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS social_consent      BOOLEAN,
  ADD COLUMN IF NOT EXISTS social_consent_at   TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS members_page_hidden BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS last_active_at      TIMESTAMPTZ;

-- Backfill BEFORE the default is set, so only rows that existed before this
-- migration are made members. New rows then start as applicants.
UPDATE fixmymedtech.profiles
   SET member_status = 'member',
       member_since  = COALESCE(member_since, created_at, NOW())
 WHERE member_status IS NULL;

ALTER TABLE fixmymedtech.profiles
  ALTER COLUMN member_status SET DEFAULT 'applicant',
  ALTER COLUMN member_status SET NOT NULL;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_member_status_check
    CHECK (member_status IN ('applicant', 'member', 'staff', 'refused'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_join_path_check
    CHECK (join_path IN ('community', 'clinic_staff'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

DO $$ BEGIN
  ALTER TABLE fixmymedtech.profiles ADD CONSTRAINT profiles_why_bme_length
    CHECK (why_bme IS NULL OR length(why_bme) <= 500);
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

-- ── Catalogue ───────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.community_roles (
  key              TEXT PRIMARY KEY,
  path             TEXT NOT NULL CHECK (path IN ('start', 'devices', 'people', 'trust', 'knowledge', 'teams', 'parts', 'leads')),
  tier             INT  NOT NULL CHECK (tier BETWEEN 0 AND 3),
  scope            TEXT NOT NULL CHECK (scope IN ('local', 'global', 'none')),
  unlock           TEXT NOT NULL CHECK (unlock IN ('auto', 'claim', 'confirmed', 'assigned')),
  names            JSONB NOT NULL,
  descriptions     JSONB NOT NULL DEFAULT '{}'::jsonb,
  linkedin_titles  JSONB NOT NULL DEFAULT '{}'::jsonb,
  sort             INT  NOT NULL DEFAULT 0,
  active           BOOLEAN NOT NULL DEFAULT TRUE,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.community_role_requirements (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  role_key   TEXT NOT NULL REFERENCES fixmymedtech.community_roles(key) ON DELETE CASCADE,
  kind       TEXT NOT NULL CHECK (kind IN ('role', 'metric', 'quest', 'confirmation')),
  ref        TEXT NOT NULL,
  threshold  INT,
  UNIQUE (role_key, kind, ref)
);

CREATE TABLE IF NOT EXISTS fixmymedtech.community_role_permissions (
  role_key    TEXT NOT NULL REFERENCES fixmymedtech.community_roles(key) ON DELETE CASCADE,
  permission  TEXT NOT NULL,
  PRIMARY KEY (role_key, permission)
);

-- ── Who holds what ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.member_roles (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  role_key        TEXT NOT NULL REFERENCES fixmymedtech.community_roles(key),
  country         TEXT,
  city            TEXT,
  team            TEXT CHECK (team IS NULL OR team IN ('software', 'data', 'hardware', 'manufacturing', 'partnerships', 'communications')),
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'removed')),
  source          TEXT NOT NULL CHECK (source IN ('auto', 'claim', 'confirmed', 'assigned', 'backfill')),
  granted_by      UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  removed_at      TIMESTAMPTZ,
  removed_reason  TEXT
);

-- Granting the same role twice (same place or team) does nothing.
CREATE UNIQUE INDEX IF NOT EXISTS ux_member_roles_holding
  ON fixmymedtech.member_roles (profile_id, role_key, COALESCE(country, ''), COALESCE(team, ''));
CREATE INDEX IF NOT EXISTS ix_member_roles_profile ON fixmymedtech.member_roles (profile_id);

CREATE TABLE IF NOT EXISTS fixmymedtech.member_quests (
  profile_id    UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  quest_key     TEXT NOT NULL,
  count         INT  NOT NULL DEFAULT 1,
  confirmed_by  UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (profile_id, quest_key)
);

-- ── Joining ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.community_applications (
  profile_id            UUID PRIMARY KEY REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  kind                  TEXT NOT NULL DEFAULT 'other' CHECK (kind IN ('engineer', 'student', 'clinician', 'other')),
  organisation          TEXT,
  motivation            TEXT,
  heard_from            TEXT,
  host_id               UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  meeting_at            TIMESTAMPTZ,
  meeting_held_at       TIMESTAMPTZ,
  meeting_confirmed_by  UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  notes                 TEXT,
  status                TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'meeting_booked', 'met', 'refused', 'withdrawn')),
  decision_reason       TEXT,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── History ─────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.community_role_changes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  action      TEXT NOT NULL,
  target      TEXT,
  before      JSONB,
  after       JSONB,
  reason      TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_community_role_changes_created ON fixmymedtech.community_role_changes (created_at DESC);

-- ── Seed: the starting tree (proposal v6, Jason 2026-10-29) ─
-- Numbers (5 faults, 25 manuals…) are a first guess, to tune with the
-- community. Edit the catalogue in SQLAdmin until the role editor exists.

INSERT INTO fixmymedtech.community_roles (key, path, tier, scope, unlock, sort, names, descriptions, linkedin_titles) VALUES
('ambassador', 'start', 0, 'local', 'auto', 0,
 '{"en":"Ambassador","fr":"Ambassadeur","es":"Embajador"}',
 '{"en":"Everyone starts here. You speak for FixMyMedTech around you and use the platform.","fr":"Tout le monde commence ici. Vous parlez de FixMyMedTech autour de vous et utilisez la plateforme.","es":"Todos empiezan aquí. Hablas de FixMyMedTech a tu alrededor y usas la plataforma."}',
 '{"en":"Ambassador, FixMyMedTech","fr":"Ambassadeur, FixMyMedTech","es":"Embajador, FixMyMedTech"}'),
('mapper', 'devices', 1, 'local', 'claim', 10,
 '{"en":"Mapper","fr":"Cartographe","es":"Cartógrafo"}',
 '{"en":"Registers devices, tags them with QR codes and keeps clinic inventories current.","fr":"Enregistre les appareils, les étiquette avec des QR codes et tient les inventaires des cliniques à jour.","es":"Registra equipos, los etiqueta con códigos QR y mantiene al día los inventarios de las clínicas."}',
 '{"en":"Mapper, FixMyMedTech","fr":"Cartographe, FixMyMedTech","es":"Cartógrafo, FixMyMedTech"}'),
('repairer', 'devices', 2, 'local', 'auto', 20,
 '{"en":"Repairer","fr":"Réparateur","es":"Reparador"}',
 '{"en":"Answers repair and maintenance requests in their area. Only Repairers order spare parts.","fr":"Répond aux demandes de réparation et de maintenance de sa zone. Seuls les Réparateurs commandent des pièces détachées.","es":"Atiende solicitudes de reparación y mantenimiento en su zona. Solo los Reparadores piden repuestos."}',
 '{"en":"Repairer, FixMyMedTech","fr":"Réparateur, FixMyMedTech","es":"Reparador, FixMyMedTech"}'),
('connector', 'people', 1, 'local', 'claim', 10,
 '{"en":"Connector","fr":"Connecteur","es":"Conector"}',
 '{"en":"Invites colleagues and clinics, and presents FixMyMedTech at events.","fr":"Invite des collègues et des cliniques, et présente FixMyMedTech lors d''événements.","es":"Invita a colegas y clínicas, y presenta FixMyMedTech en eventos."}',
 '{"en":"Connector, FixMyMedTech","fr":"Connecteur, FixMyMedTech","es":"Conector, FixMyMedTech"}'),
('clinic_champion', 'people', 1, 'local', 'claim', 15,
 '{"en":"Clinic champion","fr":"Champion de clinique","es":"Campeón de clínica"}',
 '{"en":"For clinicians: reports faults, keeps the clinic''s list current and brings colleagues.","fr":"Pour les cliniciens : signale les pannes, tient la liste de la clinique à jour et fait venir des collègues.","es":"Para clínicos: reporta fallas, mantiene la lista de la clínica al día y trae colegas."}',
 '{"en":"Clinic champion, FixMyMedTech","fr":"Champion de clinique, FixMyMedTech","es":"Campeón de clínica, FixMyMedTech"}'),
('mentor', 'people', 2, 'local', 'auto', 20,
 '{"en":"Mentor","fr":"Mentor","es":"Mentor"}',
 '{"en":"Welcomes new Ambassadors, checks their quests and answers questions.","fr":"Accueille les nouveaux Ambassadeurs, vérifie leurs quêtes et répond aux questions.","es":"Recibe a los nuevos Embajadores, revisa sus misiones y responde preguntas."}',
 '{"en":"Mentor, FixMyMedTech","fr":"Mentor, FixMyMedTech","es":"Mentor, FixMyMedTech"}'),
('verifier', 'trust', 1, 'local', 'claim', 10,
 '{"en":"Verifier","fr":"Vérificateur","es":"Verificador"}',
 '{"en":"Verifies clinics, distributors, brands and models.","fr":"Vérifie les cliniques, distributeurs, marques et modèles.","es":"Verifica clínicas, distribuidores, marcas y modelos."}',
 '{"en":"Verifier, FixMyMedTech","fr":"Vérificateur, FixMyMedTech","es":"Verificador, FixMyMedTech"}'),
('approval_host', 'trust', 2, 'local', 'confirmed', 20,
 '{"en":"Approval host","fr":"Hôte d''approbation","es":"Anfitrión de aprobación"}',
 '{"en":"Runs welcome and approval meetings, and approves clinics and new members.","fr":"Anime les réunions d''accueil et d''approbation, et approuve les cliniques et les nouveaux membres.","es":"Dirige las reuniones de bienvenida y aprobación, y aprueba clínicas y nuevos miembros."}',
 '{"en":"Approval host, FixMyMedTech","fr":"Hôte d''approbation, FixMyMedTech","es":"Anfitrión de aprobación, FixMyMedTech"}'),
('documentalist', 'knowledge', 1, 'local', 'claim', 10,
 '{"en":"Documentalist","fr":"Documentaliste","es":"Documentalista"}',
 '{"en":"Finds missing manuals and asks distributors and manufacturers for them.","fr":"Trouve les manuels manquants et les demande aux distributeurs et fabricants.","es":"Busca manuales que faltan y los pide a distribuidores y fabricantes."}',
 '{"en":"Documentalist, FixMyMedTech","fr":"Documentaliste, FixMyMedTech","es":"Documentalista, FixMyMedTech"}'),
('curator', 'knowledge', 2, 'local', 'auto', 20,
 '{"en":"Curator","fr":"Curateur","es":"Curador"}',
 '{"en":"Merges duplicate brands and models and reviews manuals others added.","fr":"Fusionne les marques et modèles en double et relit les manuels ajoutés par d''autres.","es":"Une marcas y modelos duplicados y revisa los manuales que otros añadieron."}',
 '{"en":"Curator, FixMyMedTech","fr":"Curateur, FixMyMedTech","es":"Curador, FixMyMedTech"}'),
('team_contributor', 'teams', 1, 'global', 'claim', 10,
 '{"en":"Team contributor","fr":"Contributeur d''équipe","es":"Colaborador de equipo"}',
 '{"en":"Works on one global team: software, data, hardware, manufacturing, partnerships or communications.","fr":"Travaille dans une équipe mondiale : logiciel, données, matériel, fabrication, partenariats ou communication.","es":"Trabaja en un equipo global: software, datos, hardware, fabricación, alianzas o comunicación."}',
 '{"en":"Team contributor, FixMyMedTech","fr":"Contributeur d''équipe, FixMyMedTech","es":"Colaborador de equipo, FixMyMedTech"}'),
('team_core', 'teams', 2, 'global', 'confirmed', 20,
 '{"en":"Team core","fr":"Noyau d''équipe","es":"Núcleo de equipo"}',
 '{"en":"Reviews and approves the team''s contributions.","fr":"Relit et approuve les contributions de l''équipe.","es":"Revisa y aprueba las contribuciones del equipo."}',
 '{"en":"Core team member, FixMyMedTech","fr":"Membre du noyau, FixMyMedTech","es":"Miembro del núcleo, FixMyMedTech"}'),
('part_designer', 'parts', 1, 'local', 'claim', 10,
 '{"en":"Part designer","fr":"Concepteur de pièces","es":"Diseñador de piezas"}',
 '{"en":"Reverse-engineers missing or broken spare parts: measures, photographs and models them.","fr":"Rétro-conçoit les pièces détachées manquantes ou cassées : les mesure, les photographie et les modélise.","es":"Hace ingeniería inversa de repuestos que faltan o están rotos: los mide, fotografía y modela."}',
 '{"en":"Part designer, FixMyMedTech","fr":"Concepteur de pièces, FixMyMedTech","es":"Diseñador de piezas, FixMyMedTech"}'),
('maker', 'parts', 1, 'local', 'claim', 15,
 '{"en":"Maker","fr":"Fabricant","es":"Fabricante"}',
 '{"en":"Makes non-critical parts by digital manufacturing (3D printing, laser cutting, CNC milling).","fr":"Fabrique des pièces non critiques par fabrication numérique (impression 3D, découpe laser, fraisage CNC).","es":"Fabrica piezas no críticas por fabricación digital (impresión 3D, corte láser, fresado CNC)."}',
 '{"en":"Maker, FixMyMedTech","fr":"Fabricant, FixMyMedTech","es":"Fabricante, FixMyMedTech"}'),
('design_reviewer', 'parts', 2, 'local', 'confirmed', 20,
 '{"en":"Design reviewer","fr":"Relecteur de conception","es":"Revisor de diseños"}',
 '{"en":"Reviews new part designs (dimensions, material, safety) before they enter the library.","fr":"Relit les nouvelles conceptions de pièces (dimensions, matériau, sécurité) avant leur entrée dans la bibliothèque.","es":"Revisa los nuevos diseños de piezas (dimensiones, material, seguridad) antes de que entren en la biblioteca."}',
 '{"en":"Design reviewer, FixMyMedTech","fr":"Relecteur de conception, FixMyMedTech","es":"Revisor de diseños, FixMyMedTech"}'),
('certified_maker', 'parts', 2, 'local', 'confirmed', 25,
 '{"en":"Certified maker","fr":"Fabricant certifié","es":"Fabricante certificado"}',
 '{"en":"Makes parts to order with quality control certificates, including parts beyond the non-critical list.","fr":"Fabrique des pièces sur commande avec des certificats de contrôle qualité, y compris au-delà de la liste non critique.","es":"Fabrica piezas por encargo con certificados de control de calidad, incluidas piezas fuera de la lista no crítica."}',
 '{"en":"Certified maker, FixMyMedTech","fr":"Fabricant certifié, FixMyMedTech","es":"Fabricante certificado, FixMyMedTech"}'),
('city_lead', 'leads', 3, 'local', 'assigned', 10,
 '{"en":"City lead","fr":"Responsable de ville","es":"Responsable de ciudad"}',
 '{"en":"Runs the city''s community and its monthly meetup, and tracks pending clinics.","fr":"Anime la communauté de la ville et sa rencontre mensuelle, et suit les cliniques en attente.","es":"Dirige la comunidad de la ciudad y su encuentro mensual, y sigue las clínicas pendientes."}',
 '{"en":"City lead, FixMyMedTech","fr":"Responsable de ville, FixMyMedTech","es":"Responsable de ciudad, FixMyMedTech"}'),
('country_lead', 'leads', 3, 'local', 'assigned', 20,
 '{"en":"Country lead","fr":"Responsable pays","es":"Responsable de país"}',
 '{"en":"Represents FixMyMedTech in the country and grows city teams.","fr":"Représente FixMyMedTech dans le pays et fait grandir les équipes de ville.","es":"Representa a FixMyMedTech en el país y hace crecer los equipos de ciudad."}',
 '{"en":"Country lead, FixMyMedTech","fr":"Responsable pays, FixMyMedTech","es":"Responsable de país, FixMyMedTech"}'),
('team_lead', 'leads', 3, 'global', 'assigned', 30,
 '{"en":"Global team lead","fr":"Responsable d''équipe mondiale","es":"Líder de equipo global"}',
 '{"en":"Sets a global team''s priorities and gives team core roles.","fr":"Fixe les priorités d''une équipe mondiale et attribue les rôles du noyau.","es":"Define las prioridades de un equipo global y otorga los roles del núcleo."}',
 '{"en":"Team lead, FixMyMedTech","fr":"Responsable d''équipe, FixMyMedTech","es":"Líder de equipo, FixMyMedTech"}'),
('manufacturing_hub_lead', 'leads', 3, 'local', 'assigned', 40,
 '{"en":"Manufacturing hub lead","fr":"Responsable de pôle de fabrication","es":"Responsable de centro de fabricación"}',
 '{"en":"Runs a local workshop network and sets quality rules with the reviewers.","fr":"Anime un réseau local d''ateliers et fixe les règles de qualité avec les relecteurs.","es":"Dirige una red local de talleres y fija las reglas de calidad con los revisores."}',
 '{"en":"Manufacturing hub lead, FixMyMedTech","fr":"Responsable de pôle de fabrication, FixMyMedTech","es":"Responsable de centro de fabricación, FixMyMedTech"}'),
('community_team', 'leads', 3, 'none', 'assigned', 50,
 '{"en":"Community team","fr":"Équipe communauté","es":"Equipo de comunidad"}',
 '{"en":"Reviews stories, gives roles by hand, decides applicants and moderates.","fr":"Relit les histoires, attribue des rôles à la main, décide des candidatures et modère.","es":"Revisa historias, otorga roles a mano, decide las solicitudes y modera."}',
 '{"en":"Community team, FixMyMedTech","fr":"Équipe communauté, FixMyMedTech","es":"Equipo de comunidad, FixMyMedTech"}')
ON CONFLICT (key) DO NOTHING;

INSERT INTO fixmymedtech.community_role_requirements (role_key, kind, ref, threshold) VALUES
-- Ambassador: the five welcome quests
('ambassador', 'quest', 'profile_complete', NULL),
('ambassador', 'quest', 'intro_video', NULL),
('ambassador', 'quest', 'meeting_held', NULL),
('ambassador', 'quest', 'discord_joined', NULL),
('ambassador', 'quest', 'consent_answered', NULL),
-- Tier 1: open to every Ambassador
('mapper', 'role', 'ambassador', NULL),
('connector', 'role', 'ambassador', NULL),
('clinic_champion', 'role', 'ambassador', NULL),
('verifier', 'role', 'ambassador', NULL),
('documentalist', 'role', 'ambassador', NULL),
('team_contributor', 'role', 'ambassador', NULL),
('part_designer', 'role', 'ambassador', NULL),
('maker', 'role', 'ambassador', NULL),
('maker', 'quest', 'workshop_declared', NULL),
-- Tier 2
('repairer', 'role', 'mapper', NULL),
('repairer', 'metric', 'repairs_and_maintenance', 5),
('mentor', 'role', 'connector', NULL),
('mentor', 'metric', 'invites', 3),
('approval_host', 'role', 'verifier', NULL),
('approval_host', 'metric', 'verifications', 10),
('approval_host', 'quest', 'watched_approval_meeting', 2),
('approval_host', 'confirmation', 'community_team', NULL),
('curator', 'role', 'documentalist', NULL),
('curator', 'metric', 'manuals_added', 25),
('team_core', 'role', 'team_contributor', NULL),
('team_core', 'metric', 'team_contributions', 5),
('team_core', 'confirmation', 'team_lead', NULL),
('design_reviewer', 'role', 'part_designer', NULL),
('design_reviewer', 'metric', 'designs_accepted', 3),
('design_reviewer', 'confirmation', 'community_team', NULL),
('certified_maker', 'role', 'maker', NULL),
('certified_maker', 'metric', 'parts_delivered', 5),
('certified_maker', 'quest', 'quality_certificate', NULL),
('certified_maker', 'confirmation', 'manufacturing_hub_lead', NULL)
ON CONFLICT (role_key, kind, ref) DO NOTHING;

-- Permission keys are defined in backend/utils/community.py (PERMISSIONS).
INSERT INTO fixmymedtech.community_role_permissions (role_key, permission) VALUES
('mapper', 'register_devices_for_clinics'),
('repairer', 'receive_area_repair_requests'),
('repairer', 'diagnose_outside_my_orgs'),
('repairer', 'plan_clinic_maintenance'),
('repairer', 'order_spare_parts'),
('connector', 'invite_clinics'),
('clinic_champion', 'invite_clinics'),
('mentor', 'confirm_quests'),
('mentor', 'view_applicants'),
('verifier', 'claim_verification_tasks'),
('approval_host', 'view_applicants'),
('approval_host', 'decide_applicants'),
('approval_host', 'approve_clinics'),
('approval_host', 'confirm_quests'),
('documentalist', 'add_manuals'),
('curator', 'approve_manuals'),
('curator', 'merge_entries'),
('team_core', 'approve_team_contributions'),
('part_designer', 'publish_part_designs'),
('maker', 'make_noncritical_parts'),
('design_reviewer', 'approve_part_designs'),
('certified_maker', 'supply_restricted_parts'),
('city_lead', 'view_members'),
('city_lead', 'view_applicants'),
('city_lead', 'create_local_tasks'),
('country_lead', 'view_members'),
('country_lead', 'view_applicants'),
('country_lead', 'decide_applicants'),
('country_lead', 'confirm_quests'),
('country_lead', 'create_local_tasks'),
('team_lead', 'view_members'),
('team_lead', 'approve_team_contributions'),
('manufacturing_hub_lead', 'view_members'),
('community_team', 'view_applicants'),
('community_team', 'decide_applicants'),
('community_team', 'view_members'),
('community_team', 'view_role_history'),
('community_team', 'confirm_quests'),
('community_team', 'approve_clinics')
ON CONFLICT DO NOTHING;

-- Backfill: existing members hold Ambassador in their profile country.
INSERT INTO fixmymedtech.member_roles (profile_id, role_key, country, source, granted_at)
SELECT p.id, 'ambassador', NULLIF(p.country, ''), 'backfill', COALESCE(p.member_since, NOW())
  FROM fixmymedtech.profiles p
 WHERE p.member_status = 'member'
   AND NOT EXISTS (
     SELECT 1 FROM fixmymedtech.member_roles r
      WHERE r.profile_id = p.id AND r.role_key = 'ambassador'
   );
