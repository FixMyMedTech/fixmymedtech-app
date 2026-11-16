"""Walk the engineer and clinic onboarding flow through the real pages.

Drives the running local stack like a browser would (form posts, session
cookies) and checks each step: engineer signup → welcome steps → talk
confirmed by the host → invite a clinic → clinic signup + healthsites pick →
"not now" then confirm → engineer registers a device; a clinic-invited
engineer stays locked; an uninvited clinic waits for its clinic talk.

Needs the seeded talk host (scripts/seed_test_data.py) and httpx:
    python scripts/walk_onboarding.py            # app at http://localhost:8890
    BASE_URL=http://localhost:8891 python scripts/walk_onboarding.py
Invitation tokens are read from the local database with docker compose, or
with psql when WALK_PSQL is set (e.g. WALK_PSQL="psql -h /tmp -U postgres").
Creates throwaway accounts named after the current time.
"""
import base64, os, subprocess, sys, time, uuid
import httpx

BASE = os.getenv("BASE_URL", "http://localhost:8890")
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN = str(int(time.time()))[-6:]
PW = "Pass123!"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")
results = []


def check(name, cond, extra=""):
    results.append((name, bool(cond)))
    print(("PASS " if cond else "FAIL ") + name + (f"  [{extra}]" if extra and not cond else ""))


def sql(q):
    if os.getenv("WALK_PSQL"):
        cmd = os.environ["WALK_PSQL"].split() + ["-d", "fixmymedtech", "-At", "-c", q]
    else:
        cmd = ["docker", "compose", "-f", "docker-compose.local.yml", "exec", "-T", "db",
               "psql", "-U", "postgres", "-d", "fixmymedtech", "-At", "-c", q]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=REPO)
    return out.stdout.strip()


def client():
    return httpx.Client(base_url=BASE, follow_redirects=False, timeout=60)


def login(c, email):
    r = c.post("/login", data={"email": email, "password": PW, "next": ""})
    assert r.status_code in (302, 303), r.status_code


def api_token(email):
    return httpx.post(f"{BASE}/api/auth/login", json={"email": email, "password": PW}).json()["access_token"]


def api(method, path, token, **kw):
    return httpx.request(method, f"{BASE}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=60, **kw)


# ── 1. Engineer signup ─────────────────────────────────────────
eng_email = f"eng{RUN}@fmt-demo.org"
eng = client()
r = eng.post("/signup", data={"full_name": "Kofi Engineer", "email": eng_email, "password": PW, "password2": PW})
check("engineer signup signs in and goes to Getting started", r.headers.get("location") == "/getting-started", r.status_code)
r = eng.get("/getting-started")
check("a Visitor's Getting started is the quest list", r.headers.get("location") == "/community/start/quests", r.headers.get("location"))
r = eng.get("/community/start/quests")
check("the quest list shows three welcome quests", r.status_code == 200 and "0 of 3" in r.text, r.status_code)
check("no hidden personal org created at signup",
      sql(f"select count(*) from fixmymedtech.org_users ou join fixmymedtech.users u on u.id=ou.profile_id where u.email='{eng_email}'") == "0")
r = eng.get("/home")
check("Visitor is gated from /home to the community start page", r.headers.get("location") == "/community/start", r.status_code)
r = eng.get("/new_device")
check("Visitor gated from Register device", r.headers.get("location") == "/community/start")
r = eng.get("/library")
check("Visitor can open the manual library", r.status_code == 200, r.status_code)
r = eng.post("/invite-clinic", data={"email": "x@fmt-demo.org", "message": ""})
check("Visitor cannot invite a clinic (gated)", r.status_code in (302, 303))
eng_tok = api_token(eng_email)
r = api("POST", "/api/onboarding/clinic-invitations", eng_tok, json={"email": "x@fmt-demo.org"})
check("API refuses clinic invite before quests", r.status_code == 403, r.text)

# ── 2. Quests: profile + photo (auto), talk (host) ─────────────
r = eng.post("/profile", data={"username": f"kofi{RUN}", "full_name": "Kofi Engineer", "country": "Ghana",
                               "city": "Accra", "why_bme": "Biomedical engineer at a district hospital."},
             files={"avatar": ("me.png", PNG, "image/png")})
check("profile saved", r.status_code == 200, r.status_code)
me = api("GET", "/api/onboarding/me", eng_tok).json()
q = {x["key"]: x["done"] for x in me["quests"]}
check("profile quest done", q["complete_profile"])
check("photo quest done automatically", q["profile_photo"], me)
check("talk quest not done yet, still applicant", not q["community_talk"] and me["member_status"] == "applicant")
host = client(); login(host, "host@fmt-demo.org")
r = host.get("/host")
check("host page lists the Visitor", r.status_code == 200 and "Kofi Engineer" in r.text, r.status_code)
eng_id = sql(f"select id from fixmymedtech.users where email='{eng_email}'")
r = host.post(f"/host/applicants/{eng_id}/talk")
check("host confirms the talk", r.headers.get("location") == "/host?ok=1", r.headers.get("location"))
r = eng.get("/getting-started")
check("quests done: Getting started is gone, next step is Invite a clinic", r.headers.get("location") == "/invite-clinic", r.headers.get("location"))
r = eng.get("/invite-clinic")
check("engineer is now a Contributor (invite form open)", r.status_code == 200 and 'name="email"' in r.text, r.status_code)
check("menu has no Getting started next to Invite a clinic", 'href="/getting-started"' not in r.text and 'href="/community/start"' not in r.text)
check("the three worlds show as tabs", all(f"wt w-{w}" in r.text for w in ("equipment", "work", "community")))
r = eng.get("/home")
if r.headers.get("location") == "/community/welcome":
    # Shown once when the quests are done.
    check("welcome page shown once", eng.get("/community/welcome").status_code == 200)
    r = eng.get("/home")
check("gate lifted after quests", r.status_code == 200, (r.status_code, r.headers.get("location")))

# ── 3. Invite a clinic ─────────────────────────────────────────
clinic_email = f"clinic{RUN}@fmt-demo.org"
r = eng.post("/invite-clinic", data={"email": clinic_email, "message": "Hello! Let's track your devices."})
check("invitation sent", "/invite-clinic?sent=" in (r.headers.get("location") or ""), r.status_code)
r = eng.get("/invite-clinic")
check("sent invitation listed with status Sent", clinic_email in r.text and "Sent" in r.text)
token = sql(f"select token from fixmymedtech.onboarding_invitations where email='{clinic_email}'")

# ── 4. Invited clinic signs up and picks its clinic ────────────
cl = client()
r = cl.get(f"/invite/{token}")
check("invitation page explains vision", r.status_code == 200 and "Kofi Engineer invites your clinic" in r.text, r.status_code)
r = cl.post(f"/invite/{token}", data={"full_name": "Dr. Ama Clinic", "password": PW, "password2": PW})
check("clinic account created and sent to setup", r.headers.get("location") == "/clinic/setup", r.status_code)
r = cl.get("/home")
check("clinic without clinic is sent to setup", r.headers.get("location") == "/clinic/setup")
r = cl.get("/clinic/setup?q=Accra")
check("clinic setup search page renders (healthsites without key → message)", r.status_code == 200 and "Where is your clinic" in r.text, r.status_code)
osm = f"9{RUN}"
r = cl.post("/clinic/setup/pick", data={"osm_id": osm, "osm_type": "node", "name": f"Accra Test Clinic {RUN}",
                                         "country": "GH", "region": "Greater Accra", "address": "Ring Road", "type": "clinic"})
loc = r.headers.get("location") or ""
check("picking a healthsites.io facility imports it", loc.startswith("/clinic/setup/profile?org="), loc)
org = loc.split("org=")[-1]
check("clinic records the inviting engineer",
      sql(f"select invited_by from fixmymedtech.organizations where id='{org}'") == eng_id)
r = cl.post("/clinic/setup/profile", data={"org": org, "name": f"Accra Test Clinic {RUN}", "country": "GH",
                                           "region": "Greater Accra", "address": "Ring Road 1",
                                           "contact_email": clinic_email, "type": "clinic"})
check("profile OK → engineers step", r.headers.get("location") == f"/clinic/setup/engineers?org={org}", r.headers.get("location"))
r = cl.get(f"/clinic/setup/engineers?org={org}")
check("asks to confirm the inviting engineer", "Do you confirm that Kofi Engineer can register devices" in r.text)
r = cl.post("/clinic/setup/engineers/answer", data={"org": org, "answer": "not_now"})
reg = api("GET", "/api/onboarding/registrable-clinics", eng_tok).json()
check("'not now' → engineer locked for that clinic",
      any(c["id"] == org and c["reason"] == "not_now" for c in reg["locked"]), reg)
r = eng.get("/invite-clinic")
check("engineer sees invitation status Not now", "Not now" in r.text)
check("invited_by kept after 'not now'", sql(f"select invited_by from fixmymedtech.organizations where id='{org}'") == eng_id)
dev1 = str(uuid.uuid4())
r = api("POST", "/api/devices/", eng_tok, json={"id": dev1, "name": "Test monitor", "organization_id": org})
check("device registration refused while 'not now'", r.status_code == 403, r.text)

# ── 5. Clinic confirms later from Engineers tab ────────────────
r = cl.get(f"/groups/{org}/engineers")
check("Engineers tab shows the inviter with Not now + Confirm", r.status_code == 200 and "Not now" in r.text and "Confirm" in r.text, r.status_code)
r = cl.post(f"/groups/{org}/engineers/{eng_id}/confirm")
r = cl.get(f"/groups/{org}/engineers")
check("engineer confirmed → Can register", "Can register" in r.text)

# ── 6. Engineer registers a device ─────────────────────────────
r = eng.get(f"/device/{dev1}/new")
check("Register-device wizard lists the clinic", r.status_code == 200 and f"Accra Test Clinic {RUN}" in r.text, r.status_code)
r = eng.post(f"/device/{dev1}/new", data={"name": "Patient monitor", "organization_id": org, "healthsite_id": org,
                                          "category_id": "", "acquisition_type": "purchased", "status": "operational"})
check("device registered", r.headers.get("location") == f"/device/{dev1}", r.headers.get("location"))
r = eng.get(f"/device/{dev1}")
check("responsible engineer sees the private device page", r.status_code == 200, r.status_code)
r = eng.get("/devices")
check("device in engineer's device list", "Patient monitor" in r.text)

# ── 7. Clinic adds another engineer (new account) → locked until quests ──
eng2_email = f"eng2{RUN}@fmt-demo.org"
r = cl.post(f"/groups/{org}/engineers/add", data={"email": eng2_email, "kind": "internal"})
check("engineer invitation sent by the clinic", "invited=" in (r.headers.get("location") or ""), r.headers.get("location"))
tok2 = sql(f"select token from fixmymedtech.onboarding_invitations where email='{eng2_email}'")
e2 = client()
r = e2.get(f"/invite/{tok2}")
check("engineer invitation page names the clinic", f"Accra Test Clinic {RUN} invites you" in r.text)
r = e2.post(f"/invite/{tok2}", data={"full_name": "Esi Internal", "password": PW, "password2": PW})
check("invited engineer account → Getting started", r.headers.get("location") == "/getting-started")
e2_tok = api_token(eng2_email)
reg2 = api("GET", "/api/onboarding/registrable-clinics", e2_tok).json()
check("locked engineer: named but quests pending", any(c["id"] == org and c["reason"] == "quests_pending" for c in reg2["locked"]), reg2)
r = api("POST", "/api/devices/", e2_tok, json={"id": str(uuid.uuid4()), "name": "X", "organization_id": org})
check("locked engineer cannot register (API)", r.status_code == 403
      and ("quests_pending" in r.text or "community_access_pending" in r.text), r.text)
r = e2.get(f"/device/{dev1}")
check("locked engineer gets no private device page", r.status_code in (302, 303) and r.headers.get("location") in ("/community/start", f"/d/{dev1}"), r.headers.get("location"))
r = api("GET", f"/api/devices/{dev1}", e2_tok)
check("private device API refuses locked engineer", r.status_code == 403, r.status_code)
r = cl.get(f"/groups/{org}/engineers")
check("Engineers tab shows Waiting for welcome steps", "Waiting for welcome steps" in r.text)

# ── 8. Uninvited clinic ─────────────────────────────────────────
u_email = f"uninvited{RUN}@fmt-demo.org"
uc = client()
r = uc.post("/clinic/signup", data={"full_name": "Nurse Uninvited", "email": u_email, "password": PW, "password2": PW})
check("uninvited clinic signup → setup", r.headers.get("location") == "/clinic/setup", r.headers.get("location"))
r = uc.post("/clinic/setup/create", data={"name": f"Kumasi New Clinic {RUN}", "country": "GH", "region": "Ashanti",
                                         "address": "Main St", "type": "clinic"})
loc = r.headers.get("location") or ""
uorg = loc.split("org=")[-1]
check("unlisted clinic created, flagged for healthsites.io",
      sql(f"select push_to_healthsites||','||clinic_status from fixmymedtech.organizations where id='{uorg}'") == "true,talk_pending")
r = uc.post("/clinic/setup/profile", data={"org": uorg, "name": f"Kumasi New Clinic {RUN}", "country": "GH",
                                          "region": "Ashanti", "address": "Main St", "contact_email": u_email, "type": "clinic"})
check("uninvited clinic → clinic talk step", r.headers.get("location") == f"/clinic/setup/talk?org={uorg}", r.headers.get("location"))
r = uc.get(f"/clinic/setup/talk?org={uorg}")
check("talk page explains engineers wait for the talk", "Book your clinic talk" in r.text and "once the talk has taken place" in r.text)
r = uc.post(f"/groups/{uorg}/engineers/add", data={"email": eng_email, "kind": "external"})
check("clinic names an existing contributor", "added=" in (r.headers.get("location") or ""))
reg = api("GET", "/api/onboarding/registrable-clinics", eng_tok).json()
check("engineer locked: clinic talk pending", any(c["id"] == uorg and c["reason"] == "clinic_talk_pending" for c in reg["locked"]), reg)
r = api("POST", "/api/devices/", eng_tok, json={"id": str(uuid.uuid4()), "name": "X", "organization_id": uorg})
check("registration refused before clinic talk", r.status_code == 403, r.text)
# Decision 2026-11-13: the clinic's own admin waits for the talk too.
r = api("POST", "/api/devices/", api_token(u_email), json={"id": str(uuid.uuid4()), "name": "Clinic's own device", "organization_id": uorg})
check("clinic's own admin cannot register before the talk", r.status_code == 403 and "clinic_talk_pending" in r.text, r.text)
r = host.get("/host")
check("host sees the clinic waiting for its talk", f"Kumasi New Clinic {RUN}" in r.text)
r = host.post(f"/host/clinics/{uorg}/unlock")
r = api("POST", "/api/devices/", eng_tok, json={"id": str(uuid.uuid4()), "name": "Ultrasound", "organization_id": uorg})
check("after unlock the engineer can register", r.status_code == 200, r.text)
r = api("POST", "/api/devices/", api_token(u_email), json={"id": str(uuid.uuid4()), "name": "Clinic's own device", "organization_id": uorg})
check("after unlock the clinic's admin can register", r.status_code == 200, r.text)

# ── 8b. The /groups loophole: any account creating a clinic waits too ──
r = api("POST", "/api/healthsites/", eng_tok, json={"name": f"Self-made Clinic {RUN}", "type": "clinic", "country": "GH"})
sorg = r.json().get("id") if r.status_code == 200 else None
check("a clinic created from /groups starts talk_pending", sorg and
      sql(f"select clinic_status from fixmymedtech.organizations where id='{sorg}'") == "talk_pending", r.text)
r = api("POST", "/api/devices/", eng_tok, json={"id": str(uuid.uuid4()), "name": "X", "organization_id": sorg})
check("its creator (admin) cannot register before the talk", r.status_code == 403 and "clinic_talk_pending" in r.text, r.text)

# ── 9. Old rule removed: pending join request no longer allows ──
other = "00000000-0000-0000-0000-000000000003"
api("POST", "/api/organizations/join", eng_tok, json={"org_id": other, "role": "technician"})
r = api("POST", "/api/devices/", eng_tok, json={"id": str(uuid.uuid4()), "name": "X", "organization_id": other})
check("pending join request does not allow registering", r.status_code == 403, r.text)

# ── 10. Existing accounts unaffected ───────────────────────────
t_tok = api_token("tech@mulago.org")
r = api("POST", "/api/devices/", t_tok, json={"id": str(uuid.uuid4()), "name": "Seed tech device",
                                              "organization_id": "00000000-0000-0000-0000-000000000001"})
check("existing technician can still register (backfill)", r.status_code == 200, r.text)
old = client(); login(old, "admin@mulago.org")
check("existing admin not gated", old.get("/home").status_code == 200)

# ── 11. i18n smoke: French and Spanish pages render ─────────────
for lang, word in (("fr", "Inviter une clinique"), ("es", "Invitar a una clínica")):
    eng.post("/lang", data={"lang": lang}, headers={"Referer": "/invite-clinic"})
    r = eng.get("/invite-clinic")
    check(f"Invite a clinic in {lang}", word in r.text)
eng.post("/lang", data={"lang": "en"})

failed = [n for n, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
print("ACCOUNTS", eng_email, clinic_email, eng2_email, u_email, "ORG", org, "UORG", uorg, "DEV", dev1)
sys.exit(1 if failed else 0)
