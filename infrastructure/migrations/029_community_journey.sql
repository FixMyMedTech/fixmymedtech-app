-- 029_community_journey.sql
-- Community journey: joining, community teams and achievements.
-- Docs: docs/docs/community-guide.md (how to use), docs/docs/community-journey.md (plan).
--
-- Teams are NOT org roles. org_users.role (admin, technician, …) decides what
-- someone can do inside one organization. A community team (Communicator,
-- Community Builder, Clinics Connector) is what a member does for the
-- community. Each person in a team is a candidate, a member or a lead.
--
--   community_teams         the three teams; texts editable by each team's lead
--   team_members            who is in which team, and at which level
--   achievements            what members can earn, each with 10 star levels
--   achievement_records     achievements recognised by a team member
--   member_quests           welcome quests and other one-off steps
--   community_applications  the /join answers and the welcome call
--   community_changes       append-only log, shown in the History tab
--
-- New profile columns: member_status (applicant → member; staff for invited
-- clinic staff; refused), join_path, city, story fields, consent, activity.
-- Every profile that exists before this migration becomes a member, so nobody
-- already on the platform loses access.
--
-- An earlier draft of this migration (029_community_roles, never merged) made
-- a 21-role skill tree. Its tables are dropped below if a local database has
-- them. Idempotent: safe to re-run.

DROP TABLE IF EXISTS fixmymedtech.community_role_permissions CASCADE;
DROP TABLE IF EXISTS fixmymedtech.community_role_requirements CASCADE;
DROP TABLE IF EXISTS fixmymedtech.member_roles CASCADE;
DROP TABLE IF EXISTS fixmymedtech.community_roles CASCADE;
ALTER TABLE IF EXISTS fixmymedtech.community_role_changes RENAME TO community_changes;
ALTER INDEX IF EXISTS fixmymedtech.ix_community_role_changes_created RENAME TO ix_community_changes_created;

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

-- ── Teams ───────────────────────────────────────────────────
-- Texts are JSON objects keyed by language: {"en": "...", "fr": "...", "es": "..."}.
-- tasks is {"en": ["...", "..."], ...}: what the team does, one line each.

CREATE TABLE IF NOT EXISTS fixmymedtech.community_teams (
  key              TEXT PRIMARY KEY,
  sort             INT  NOT NULL DEFAULT 0,
  names            JSONB NOT NULL,
  descriptions     JSONB NOT NULL DEFAULT '{}'::jsonb,
  tasks            JSONB NOT NULL DEFAULT '{}'::jsonb,
  linkedin_titles  JSONB NOT NULL DEFAULT '{}'::jsonb,
  active           BOOLEAN NOT NULL DEFAULT TRUE,
  updated_by       UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fixmymedtech.team_members (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id      UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  team_key        TEXT NOT NULL REFERENCES fixmymedtech.community_teams(key),
  level           TEXT NOT NULL CHECK (level IN ('candidate', 'member', 'lead')),
  status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'removed')),
  granted_by      UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  granted_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  removed_at      TIMESTAMPTZ,
  removed_reason  TEXT
);
-- One active place per person and team; removed rows stay as history.
CREATE UNIQUE INDEX IF NOT EXISTS ux_team_members_active
  ON fixmymedtech.team_members (profile_id, team_key) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS ix_team_members_profile ON fixmymedtech.team_members (profile_id);

-- ── Achievements ────────────────────────────────────────────
-- source 'metric': counted by the platform (metric = a count name in
-- backend/utils/community.py). source 'recognised': a member of the team
-- in team_key records it for someone.
-- levels: the count needed for each of the 10 star levels, ascending.

CREATE TABLE IF NOT EXISTS fixmymedtech.achievements (
  key           TEXT PRIMARY KEY,
  team_key      TEXT NOT NULL REFERENCES fixmymedtech.community_teams(key),
  source        TEXT NOT NULL CHECK (source IN ('metric', 'recognised')),
  metric        TEXT,
  levels        INT[] NOT NULL CHECK (array_length(levels, 1) = 10),
  sort          INT  NOT NULL DEFAULT 0,
  names         JSONB NOT NULL,
  descriptions  JSONB NOT NULL DEFAULT '{}'::jsonb,
  active        BOOLEAN NOT NULL DEFAULT TRUE,
  CHECK (source <> 'metric' OR metric IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS fixmymedtech.achievement_records (
  id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id       UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  achievement_key  TEXT NOT NULL REFERENCES fixmymedtech.achievements(key),
  count            INT  NOT NULL DEFAULT 1 CHECK (count BETWEEN 1 AND 100),
  note             TEXT,
  recognised_by    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_achievement_records_profile ON fixmymedtech.achievement_records (profile_id);

-- ── Quests, joining, history ────────────────────────────────

CREATE TABLE IF NOT EXISTS fixmymedtech.member_quests (
  profile_id    UUID NOT NULL REFERENCES fixmymedtech.profiles(id) ON DELETE CASCADE,
  quest_key     TEXT NOT NULL,
  count         INT  NOT NULL DEFAULT 1,
  confirmed_by  UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (profile_id, quest_key)
);

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

CREATE TABLE IF NOT EXISTS fixmymedtech.community_changes (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id    UUID REFERENCES fixmymedtech.profiles(id) ON DELETE SET NULL,
  action      TEXT NOT NULL,
  target      TEXT,
  before      JSONB,
  after       JSONB,
  reason      TEXT,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_community_changes_created ON fixmymedtech.community_changes (created_at DESC);

-- ── Seed (Jason, 2026-11-04) ────────────────────────────────

INSERT INTO fixmymedtech.community_teams (key, sort, names, descriptions, tasks, linkedin_titles) VALUES
('communicator', 1,
 '{"en":"Communicator","fr":"Communicant","es":"Comunicador"}',
 '{"en":"Tells the world what the community does.","fr":"Raconte au monde ce que fait la communauté.","es":"Cuenta al mundo lo que hace la comunidad."}',
 '{"en":["Uses the community''s content to publish outside the community (LinkedIn, Twitter, Instagram, WhatsApp…)","Motivates the community to engage with these posts","Promotes the members of the community outside of it","Works on how the project is presented to the outside world","Supports the creation of videos and pictures","Manages the media the community can use to communicate"],
   "fr":["Utilise le contenu de la communauté pour publier à l''extérieur (LinkedIn, Twitter, Instagram, WhatsApp…)","Motive la communauté à réagir à ces publications","Met en valeur les membres de la communauté à l''extérieur","Travaille la présentation du projet au monde extérieur","Aide à créer des vidéos et des photos","Gère les médias que la communauté peut utiliser pour communiquer"],
   "es":["Usa el contenido de la comunidad para publicar fuera de ella (LinkedIn, Twitter, Instagram, WhatsApp…)","Motiva a la comunidad a interactuar con esas publicaciones","Da a conocer a los miembros de la comunidad fuera de ella","Trabaja en cómo se presenta el proyecto al mundo","Apoya la creación de vídeos y fotos","Gestiona los medios que la comunidad puede usar para comunicar"]}',
 '{"en":"Communicator, FixMyMedTech","fr":"Communicant, FixMyMedTech","es":"Comunicador, FixMyMedTech"}'),
('community_builder', 2,
 '{"en":"Community Builder","fr":"Bâtisseur de communauté","es":"Constructor de comunidad"}',
 '{"en":"Makes the community a place people want to join and stay in.","fr":"Fait de la communauté un lieu que l''on veut rejoindre et où l''on reste.","es":"Hace de la comunidad un lugar al que la gente quiere unirse y quedarse."}',
 '{"en":["Organises events","Welcomes new members","Answers questions on WhatsApp, Discord and elsewhere","Collects and structures feedback so it becomes features","Guides new users to engage more and, if they wish, to join a team"],
   "fr":["Organise des événements","Accueille les nouveaux membres","Répond aux questions sur WhatsApp, Discord et ailleurs","Recueille et structure les retours pour en faire des fonctionnalités","Guide les nouveaux utilisateurs pour qu''ils s''engagent davantage et, s''ils le souhaitent, rejoignent une équipe"],
   "es":["Organiza eventos","Da la bienvenida a los nuevos miembros","Responde preguntas en WhatsApp, Discord y otros canales","Recoge y ordena los comentarios para convertirlos en funciones","Guía a los nuevos usuarios para que participen más y, si quieren, se unan a un equipo"]}',
 '{"en":"Community Builder, FixMyMedTech","fr":"Bâtisseur de communauté, FixMyMedTech","es":"Constructor de comunidad, FixMyMedTech"}'),
('clinics_connector', 3,
 '{"en":"Clinics Connector","fr":"Connecteur de cliniques","es":"Conector de clínicas"}',
 '{"en":"Brings the platform to clinics on the ground.","fr":"Amène la plateforme dans les cliniques, sur le terrain.","es":"Lleva la plataforma a las clínicas, sobre el terreno."}',
 '{"en":["Promotes the platform on the ground","Builds promotional material with the Communicators","Helps the community team train new users"],
   "fr":["Fait connaître la plateforme sur le terrain","Prépare du matériel promotionnel avec les Communicants","Aide l''équipe communauté à former les nouveaux utilisateurs"],
   "es":["Promueve la plataforma sobre el terreno","Prepara material promocional con los Comunicadores","Ayuda al equipo de comunidad a formar a nuevos usuarios"]}',
 '{"en":"Clinics Connector, FixMyMedTech","fr":"Connecteur de cliniques, FixMyMedTech","es":"Conector de clínicas, FixMyMedTech"}')
ON CONFLICT (key) DO NOTHING;

-- Level thresholds are a first guess; edit them in SQLAdmin (/admin → Achievements).
INSERT INTO fixmymedtech.achievements (key, team_key, source, metric, levels, sort, names, descriptions) VALUES
('mapper', 'clinics_connector', 'metric', 'devices_registered', '{1,5,10,20,35,50,75,100,150,200}', 1,
 '{"en":"Mapper","fr":"Cartographe","es":"Cartógrafo"}',
 '{"en":"Add devices to the platform. Counted automatically.","fr":"Ajoutez des dispositifs à la plateforme. Compté automatiquement.","es":"Añade equipos a la plataforma. Se cuenta automáticamente."}'),
('ambassador', 'clinics_connector', 'recognised', NULL, '{1,3,5,10,15,25,40,60,80,100}', 2,
 '{"en":"Ambassador","fr":"Ambassadeur","es":"Embajador"}',
 '{"en":"Share and publish social media posts about the community.","fr":"Partagez et publiez des messages sur les réseaux sociaux à propos de la communauté.","es":"Comparte y publica mensajes en redes sociales sobre la comunidad."}'),
('supporter', 'community_builder', 'recognised', NULL, '{1,3,5,10,15,25,40,60,80,100}', 3,
 '{"en":"Supporter","fr":"Soutien","es":"Apoyo"}',
 '{"en":"Help a fellow engineer find a solution to their problem.","fr":"Aidez un collègue ingénieur à trouver une solution à son problème.","es":"Ayuda a un colega ingeniero a encontrar una solución a su problema."}'),
('event_organiser', 'community_builder', 'recognised', NULL, '{1,2,3,5,8,12,16,20,25,30}', 4,
 '{"en":"Event Organiser","fr":"Organisateur d''événements","es":"Organizador de eventos"}',
 '{"en":"Organise an event for the community.","fr":"Organisez un événement pour la communauté.","es":"Organiza un evento para la comunidad."}'),
('active_builder', 'community_builder', 'recognised', NULL, '{1,3,5,10,15,20,30,40,50,60}', 5,
 '{"en":"Active Builder","fr":"Bâtisseur actif","es":"Constructor activo"}',
 '{"en":"Take part in community meetings.","fr":"Participez aux réunions de la communauté.","es":"Participa en las reuniones de la comunidad."}')
ON CONFLICT (key) DO NOTHING;
