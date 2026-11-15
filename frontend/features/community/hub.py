# features/community/hub.py — discover the app and nourish it.
#
#   next_step(...)        one next step per world, derived from existing API
#   next_step_card(...)   data (no new table); shown until done, then gone.
#                         Used at the top of /tasks (Work), /dashboard
#                         (Equipment, clinic accounts) and /community.
#   tour_panel(...)       first-visit tour of the three worlds (/home and
#                         /community), dismissed with "Got it".
#   needs_section(...)    "What the app needs now": live counts, one tile per
#                         need, each an entry to the page where it is done.
#   discover_section(...) "Discover the app": Learn the app, the three worlds,
#                         your next step elsewhere.
#
# Every API call here is wrapped: a failure hides the piece, never the page.
# Strings are the hub.* keys of _HUB_STRINGS in i18n.py.

import asyncio
import hashlib

from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.calls.api as calls_api
import features.community.api as community_api
import features.groups.api as groups_api
import features.onboarding.api as ob_api
from components import lucide, LUCIDE_ICONS, WORLD_TONES, WORLD_ICONS, user_worlds
from i18n import t as make_t

rt = APIRouter()

# Lucide icons this module needs, registered here (not in components.py) so
# that parallel branches touching LUCIDE_ICONS merge cleanly.
for _name, _body in {
    "arrow-right": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "compass": '<path d="m16.24 7.76-1.804 5.411a2 2 0 0 1-1.265 1.265L7.76 16.24l1.804-5.411a2 2 0 0 1 1.265-1.265z"/>'
               '<circle cx="12" cy="12" r="10"/>',
    "sprout": '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/>'
              '<path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/>'
              '<path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>',
    "graduation-cap": '<path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z"/>'
                      '<path d="M22 10v6"/><path d="M6 12.5V16a6 3 0 0 0 12 0v-3.5"/>',
    "circle-check": '<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>',
    "user-plus": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                 '<line x1="19" x2="19" y1="8" y2="14"/><line x1="22" x2="16" y1="11" y2="11"/>',
    "book-open": '<path d="M12 7v14"/><path d="M3 18a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h5a4 4 0 0 1 4 4 4 4 0 0 1 4-4h5a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1h-6a3 3 0 0 0-3 3 3 3 0 0 0-3-3z"/>',
}.items():
    LUCIDE_ICONS.setdefault(_name, _body)


HUB_CSS = """
.hub-sec { margin:28px 0 12px; }
.hub-sec .sec-h { margin-bottom:12px; }
.hub-sec .sec-h p { flex-basis:100%; margin:0; color:var(--text-muted); font-size:14px; }
/* Next step: one card, one action. */
.nstep { --tone: var(--primary); --tone-tint: var(--primary-tint); display:flex; align-items:center; gap:16px; flex-wrap:wrap; padding:16px 18px; margin-bottom:20px; background:var(--surface); border:1px solid var(--border); border-left:5px solid var(--tone); border-radius:var(--radius-card); box-shadow:var(--shadow-card); }
.nstep.t-eng { --tone: var(--accent); --tone-tint: var(--accent-tint); } .nstep.t-lead { --tone: var(--lead); --tone-tint: var(--lead-tint); }
.nstep-ico { width:48px; height:48px; border-radius:14px; display:grid; place-items:center; background:var(--tone); color:var(--surface); flex-shrink:0; }
.nstep-ico svg { width:24px; height:24px; }
.nstep-txt { flex:1 1 240px; min-width:0; display:flex; flex-direction:column; gap:2px; }
.nstep-txt .eyebrow { font-size:12px; font-weight:700; letter-spacing:.06em; text-transform:uppercase; color:var(--tone); }
.nstep-txt b { font-size:1.05rem; color:var(--text); }
.nstep-txt span { font-size:14px; color:var(--text-muted); }
@media (max-width:640px){ .nstep .btn { width:100%; justify-content:center; } }
/* Tour: three coloured cards and "Got it". */
.tour { padding:18px; margin-bottom:20px; border-radius:var(--radius-panel); background:var(--sunken); border:1px solid var(--border); }
.tour-head { display:flex; align-items:flex-start; gap:12px; justify-content:space-between; flex-wrap:wrap; margin-bottom:14px; }
.tour-head h2 { font-size:1.2rem; margin:0; }
.tour-head p { margin:2px 0 0; font-size:14px; color:var(--text-muted); }
.tour-foot { display:flex; justify-content:flex-end; margin:14px 0 0; }
@media (max-width:640px){ .tour { padding:14px; } .tour-card { padding:12px; } .tour-foot .btn { width:100%; justify-content:center; } }
.tour-cards { display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; }
.tour-card { --tone: var(--primary); display:flex; gap:12px; align-items:flex-start; padding:14px; background:var(--surface); border:1px solid var(--border); border-top:4px solid var(--tone); border-radius:var(--radius-card); }
.tour-card.w-work { --tone: var(--accent); } .tour-card.w-community { --tone: var(--lead); }
.tour-card .ico { width:40px; height:40px; border-radius:12px; display:grid; place-items:center; background:var(--tone); color:var(--surface); flex-shrink:0; }
.tour-card .ico svg { width:20px; height:20px; }
.tour-card b { display:block; color:var(--tone); }
.tour-card span { font-size:14px; color:var(--text); }
/* Discover: a short row of cards. */
.disc { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; align-items:start; }
.disc-card { --tone: var(--primary); --tone-tint: var(--primary-tint); display:flex; flex-direction:column; gap:10px; padding:16px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-card); box-shadow:var(--shadow-card); color:var(--text); text-decoration:none; transition:transform .15s, box-shadow .15s; }
.disc-card.t-eng { --tone: var(--accent); --tone-tint: var(--accent-tint); } .disc-card.t-lead { --tone: var(--lead); --tone-tint: var(--lead-tint); }
a.disc-card:hover { transform:translateY(-2px); box-shadow:var(--shadow-float); color:var(--text); }
.disc-card .ico { width:40px; height:40px; border-radius:12px; display:grid; place-items:center; background:var(--tone-tint); color:var(--tone); }
.disc-card .ico svg { width:22px; height:22px; }
.disc-card b { font-size:1rem; }
.disc-card p { margin:0; font-size:14px; color:var(--text-muted); }
.disc-card .go { margin-top:auto; display:inline-flex; align-items:center; gap:6px; font-size:14px; font-weight:600; color:var(--primary); }
.disc-card .go svg { width:16px; height:16px; }
.mini-worlds { display:flex; flex-direction:column; gap:6px; }
.mini-world { --tone: var(--primary); --tone-tint: var(--primary-tint); display:flex; align-items:center; gap:10px; padding:6px 8px; border-radius:10px; background:var(--tone-tint); color:var(--text); text-decoration:none; font-size:14px; min-height:44px; box-sizing:border-box; }
.mini-world.w-work { --tone: var(--accent); --tone-tint: var(--accent-tint); } .mini-world.w-community { --tone: var(--lead); --tone-tint: var(--lead-tint); }
.mini-world .dot { width:28px; height:28px; border-radius:8px; display:grid; place-items:center; background:var(--tone); color:var(--surface); flex-shrink:0; }
.mini-world .dot svg { width:16px; height:16px; }
.mini-world b { display:block; color:var(--tone); font-size:14px; }
.mini-world span { display:block; color:var(--text-muted); font-size:12px; line-height:1.3; }
/* Needs: a number, a label, one action. */
.needs { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }
.need { --tone: var(--primary); display:flex; flex-direction:column; gap:6px; padding:16px; background:var(--surface); border:1px solid var(--border); border-top:4px solid var(--tone); border-radius:var(--radius-card); box-shadow:var(--shadow-card); color:var(--text); text-decoration:none; transition:transform .15s, box-shadow .15s; min-width:0; }
.need.t-eng { --tone: var(--accent); } .need.t-lead { --tone: var(--lead); }
.need:hover { transform:translateY(-2px); box-shadow:var(--shadow-float); color:var(--text); }
.need-top { display:flex; align-items:center; justify-content:space-between; gap:8px; }
.need-top .ico { color:var(--tone); } .need-top .ico svg { width:22px; height:22px; display:block; }
.need-num { font-size:32px; line-height:1; font-weight:800; font-variant-numeric:tabular-nums; letter-spacing:-.02em; color:var(--tone); }
.need-lbl { font-size:14px; font-weight:600; }
.need-sub { font-size:12px; color:var(--text-muted); }
.need-go { margin-top:auto; padding-top:6px; display:inline-flex; align-items:center; gap:6px; font-size:14px; font-weight:600; color:var(--primary); }
.need-go svg { width:16px; height:16px; }
.caught { display:flex; align-items:center; gap:10px; flex-wrap:wrap; margin-top:12px; padding:10px 14px; border-radius:var(--radius-card); background:var(--ok-tint); color:var(--text); font-size:14px; }
.caught > svg { width:20px; height:20px; color:var(--ok); flex-shrink:0; }
.caught.all { padding:18px; }
.caught .chips { display:flex; flex-wrap:wrap; gap:6px; }
.caught .chips span { font-size:12px; font-weight:600; padding:2px 9px; border-radius:var(--radius-pill); background:var(--surface); color:var(--text-muted); }
/* Teams, achievements, counters: kept, more compact. */
.hub-compact { display:grid; gap:12px; margin-top:28px; }
.hub-compact .cj-card { padding:14px 16px; }
.cj > .nstep, .cj > .tour { margin-bottom:0; }
.cj > .hub-sec { margin:8px 0 0; }
.cj > .hub-compact { margin-top:8px; }
@media (prefers-reduced-motion: reduce) { .disc-card, .need { transition:none; } a.disc-card:hover, .need:hover { transform:none; } }
"""


async def _safe(coro, default=None):
    try:
        return await coro
    except Exception:
        return default


def _is_member(req) -> bool:
    return req.session.get("member_status", "member") == "member"


def _is_engineer(req) -> bool:
    return (req.session.get("user_account_kind") or "engineer") == "engineer"


# ══════════════════════════════════════════════════════════════
# NEXT STEPS
# ══════════════════════════════════════════════════════════════
# A step: {"world", "icon", "key", "href"}; hub.step.<key>.title/.text/.cta
# carry the words. None means nothing to do in that world.

def _step(world, icon, key, href):
    return {"world": world, "icon": icon, "key": key, "href": href}


async def work_step(token, *, cme=None, inbox=None, invitations=None, clinics=None):
    """Engineer (member): invite a clinic → register a device → answer a
    request → nothing. Any piece may be passed in when the page has it."""
    cme, inbox, invitations, clinics = await asyncio.gather(
        _safe(community_api.get_me(token), {}) if cme is None else _done(cme),
        _safe(calls_api.inbox(token), {}) if inbox is None else _done(inbox),
        _safe(ob_api.my_clinic_invitations(token), None) if invitations is None else _done(invitations),
        _safe(ob_api.my_clinics(token), None) if clinics is None else _done(clinics),
    )
    if not cme:
        return None
    metrics = cme.get("metrics") or {}
    devices = int(metrics.get("devices_registered") or 0)
    if devices == 0:
        if invitations is None or clinics is None:
            return None                     # can't tell: say nothing
        active = [i for i in invitations if i.get("status") != "cancelled"]
        if not active and not clinics:
            return _step("work", "mail", "invite_clinic", "/invite-clinic")
        return _step("work", "plus", "first_device", "/new_device")
    inbox = inbox or {}
    if inbox.get("open") and not inbox.get("mine") and not int(metrics.get("faults_resolved") or 0):
        return _step("work", "inbox", "first_request", "/requests")
    return None


async def community_step(token, *, cme=None, board=None):
    """Member: join a team (become a candidate) → take a first task → nothing."""
    cme, board = await asyncio.gather(
        _safe(community_api.get_me(token), {}) if cme is None else _done(cme),
        _safe(community_api.task_board(token), {}) if board is None else _done(board),
    )
    if not cme:
        return None
    if not (cme.get("teams") or []):
        return _step("community", "users", "meet_team", "/community/achievements")
    if board and not board.get("mine") and not board.get("my_points") and board.get("open") and board.get("can_take"):
        return _step("community", "board", "first_task", "/community/tasks#open")
    return None


async def equipment_step(req, token, *, total_devices=None):
    """Clinic accounts: add a first device (or, while the clinic waits for its
    clinic talk, book the talk: devices can't be added before it) → invite a
    colleague (clinic with a single member, admins only) → nothing."""
    if total_devices is None:
        import features.dashboard.api as dashboard_api
        stats = await _safe(dashboard_api.get_dashboard_stats(token), None)
        if stats is None:
            return None
        total_devices = stats.get("total_devices", 0)
    mine = await _safe(ob_api.clinic_mine(token), {}) or {}
    admin_orgs = mine.get("clinics") or []
    if not total_devices:
        if not auth_helper.adds_devices(req):
            return None
        if admin_orgs and all(c.get("clinic_status") == "talk_pending" for c in admin_orgs):
            return _step("equipment", "calendar", "book_talk", f"/clinic/setup/talk?org={admin_orgs[0]['id']}")
        return _step("equipment", "plus", "add_device", "/new_device")
    if not admin_orgs:
        return None
    org_id = str(admin_orgs[0].get("id"))
    members = await _safe(groups_api.get_organization_members(token, org_id), None)
    if members is not None and len(members) <= 1:
        return _step("equipment", "user-plus", "invite_colleague", f"/groups/{org_id}")
    return None


async def _done(value):
    return value


def next_step_card(step, _):
    """The next step, or "" when there is none."""
    if not step:
        return ""
    tone = WORLD_TONES.get(step["world"], "")
    key = f"hub.step.{step['key']}"
    return Div(
        Span(lucide(step["icon"]), cls="nstep-ico", aria_hidden="true"),
        Div(Span(_("hub.next_step"), cls="eyebrow"), B(_(f"{key}.title")), Span(_(f"{key}.text")),
            cls="nstep-txt"),
        A(_(f"{key}.cta"), lucide("arrow-right"), href=step["href"], cls="btn btn-primary"),
        cls="nstep" + (f" t-{tone}" if tone else ""),
        role="region", aria_label=_("hub.next_step"),
    )


async def next_step_block(req, token, world, _, **known):
    """Style + card for the top of a world's main page; "" on any failure."""
    try:
        if not _is_member(req) and world != "equipment":
            return ""
        if world == "work":
            step = await work_step(token, **known) if _is_engineer(req) else None
        elif world == "community":
            step = await community_step(token, **known) if _is_engineer(req) else None
        elif world == "equipment":
            step = await equipment_step(req, token, **known) if not _is_engineer(req) else None
        else:
            step = None
        return Div(Style(HUB_CSS), next_step_card(step, _)) if step else ""
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════
# FIRST-VISIT TOUR
# ══════════════════════════════════════════════════════════════
# Dismissal: the session key "hub_tour_seen" (this login) plus a long-lived
# cookie listing short hashes of the accounts that pressed "Got it" on this
# browser (survives logout; the session is cleared then). No migration, so
# another browser or phone shows the tour once more.

TOUR_COOKIE = "fmt_tour_seen"
TOUR_WORLDS = ("equipment", "work", "community")


def _user_tag(req) -> str:
    who = (req.session.get("user_email") or req.session.get("user_username") or "").lower()
    return hashlib.sha256(who.encode()).hexdigest()[:10] if who else ""


def tour_seen(req) -> bool:
    if req.session.get("hub_tour_seen"):
        return True
    tag = _user_tag(req)
    return bool(tag) and tag in (req.cookies.get(TOUR_COOKIE) or "").split(".")


def tour_panel(req, lang, back="/home"):
    """The three worlds, once, for accounts that have more than one."""
    _ = make_t(lang)
    try:
        worlds = user_worlds(lang)
    except Exception:
        return ""
    if len(worlds) < 2 or tour_seen(req):
        return ""
    cards = [Div(Span(lucide(w["icon"]), cls="ico", aria_hidden="true"),
                 Div(B(w["label"]), Span(_(f"hub.tour.{w['key']}"))),
                 cls=f"tour-card w-{w['key']}")
             for w in worlds]
    return Div(
        Style(HUB_CSS),
        Div(Div(H2(_("hub.tour.title")), P(_("hub.tour.text"))), cls="tour-head"),
        Div(*cards, cls="tour-cards"),
        # After the cards: on a phone you read them, then press "Got it".
        Form(Input(type="hidden", name="back", value=back),
             Button(lucide("check"), _("hub.tour.got_it"), type="submit", cls="btn btn-primary"),
             method="post", action="/hub/tour/dismiss", cls="tour-foot"),
        cls="tour", id="tour", role="region", aria_label=_("hub.tour.title"),
    )


@rt("/hub/tour/dismiss", methods=["post"])
async def tour_dismiss(req, back: str = "/home"):
    back = back if back.startswith("/") and not back.startswith("//") else "/home"
    req.session["hub_tour_seen"] = "1"
    resp = RedirectResponse(back, status_code=303)
    tag = _user_tag(req)
    if tag:
        tags = [x for x in (req.cookies.get(TOUR_COOKIE) or "").split(".") if x and x != tag][-19:] + [tag]
        resp.set_cookie(TOUR_COOKIE, ".".join(tags), max_age=60 * 60 * 24 * 365 * 2,
                        httponly=True, samesite="lax", path="/")
    return resp


# ══════════════════════════════════════════════════════════════
# COMMUNITY HOME: DISCOVER + NOURISH
# ══════════════════════════════════════════════════════════════

async def load_hub(req, token, cme):
    """Everything the community home needs, in parallel; each piece is None
    when its call failed or does not apply to this person."""
    host = bool(req.session.get("user_is_talk_host"))
    board, review, inbox, invitations, clinics, visitors, waiting = await asyncio.gather(
        _safe(community_api.task_board(token)),
        _safe(community_api.claims_to_review(token)),
        _safe(calls_api.inbox(token)),
        _safe(ob_api.my_clinic_invitations(token)),
        _safe(ob_api.my_clinics(token)),
        _safe(ob_api.host_applicants(token)) if host else _done(None),
        _safe(ob_api.host_clinics(token)) if host else _done(None),
    )
    return {"me": cme, "board": board, "review": review, "inbox": inbox, "invitations": invitations,
            "clinics": clinics, "visitors": visitors, "waiting_clinics": waiting}


def _needs(data, req) -> list[dict]:
    """[{key, n, tone, icon, href, sub}] for every need this person can act on
    (n may be 0: it then shows in the "all caught up" line)."""
    out = []
    board = data.get("board")
    if board is not None:
        open_ = board.get("open") or []
        manuals = sum(1 for t in open_ if t.get("kind") == "find_manual")
        out.append({"key": "tasks", "n": len(open_), "tone": "lead", "icon": "board",
                    "href": "/community/tasks#open", "sub": manuals})
        to_check = board.get("to_check") or []
        if to_check:
            out.append({"key": "check", "n": len(to_check), "tone": "lead", "icon": "clipboard",
                        "href": "/community/tasks#check"})
    review = data.get("review")
    if review and review.get("can_review"):
        claims = [c for c in review.get("claims") or [] if not c.get("i_confirmed")]
        out.append({"key": "claims", "n": len(claims), "tone": "lead", "icon": "check", "href": "/lead#claims"})
    inbox = data.get("inbox")
    if inbox is not None and inbox.get("can_offer"):
        out.append({"key": "requests", "n": len(inbox.get("open") or []), "tone": "eng", "icon": "inbox",
                    "href": "/requests"})
    if data.get("visitors") is not None:
        n = sum(1 for a in data["visitors"] if not (a.get("quests") or {}).get("community_talk"))
        out.append({"key": "visitors", "n": n, "tone": "lead", "icon": "mic", "href": "/host"})
    if data.get("waiting_clinics") is not None:
        out.append({"key": "clinics", "n": len(data["waiting_clinics"]), "tone": "eng", "icon": "mic",
                    "href": "/host"})
    if data.get("invitations") is not None:
        n = sum(1 for i in data["invitations"] if i.get("status") in ("sent", "account_created"))
        out.append({"key": "invites", "n": n, "tone": "eng", "icon": "mail", "href": "/invite-clinic"})
    return out


def needs_section(data, req, _):
    needs = _needs(data, req)
    live = [n for n in needs if n["n"]]
    quiet = [n for n in needs if not n["n"]]

    def tile(n):
        k = f"hub.need.{n['key']}"
        sub = _("hub.need.tasks.manuals").format(n=n["sub"]) if n["key"] == "tasks" and n.get("sub") else _(f"{k}.sub")
        return A(Div(Span(str(n["n"]), cls="need-num"), Span(lucide(n["icon"]), cls="ico", aria_hidden="true"),
                     cls="need-top"),
                 Span(_(f"{k}.label"), cls="need-lbl"),
                 Span(sub, cls="need-sub"),
                 Span(_(f"{k}.cta"), lucide("arrow-right"), cls="need-go"),
                 href=n["href"], cls=f"need t-{n['tone']}")

    caught = ""
    if quiet and live:
        caught = Div(lucide("circle-check"), Span(_("hub.caught_up_on")),
                     Div(*[Span(_(f"hub.need.{n['key']}.label")) for n in quiet], cls="chips"), cls="caught")
    elif not live:
        caught = Div(lucide("circle-check"),
                     Div(B(_("hub.all_caught_up")), Div(_("hub.all_caught_up_text")),
                         Div(*[Span(_(f"hub.need.{n['key']}.label")) for n in quiet], cls="chips",
                             style="margin-top:8px;") if quiet else ""),
                     A(_("hub.post_task"), href="/community/tasks#new-task", cls="btn btn-secondary btn-sm",
                       style="margin-left:auto;") if (data.get("board") or {}).get("can_create") else "",
                     cls="caught all")

    return Div(
        Div(Span(lucide("sprout"), cls="sec-ico ok", aria_hidden="true"), H2(_("hub.nourish_title")),
            P(_("hub.nourish_text")), cls="sec-h"),
        Div(*[tile(n) for n in live], cls="needs") if live else "",
        caught,
        cls="hub-sec", id="needs",
    )


def discover_section(lang, _, other_step=None):
    try:
        worlds = user_worlds(lang)
    except Exception:
        worlds = []
    learn = A(Span(lucide("graduation-cap"), cls="ico", aria_hidden="true"),
              B(_("hub.learn.title")), P(_("hub.learn.text")),
              Span(_("hub.learn.cta"), lucide("arrow-right"), cls="go"),
              href="/community/guides", cls="disc-card t-lead")
    world_card = Div(Span(lucide("compass"), cls="ico", aria_hidden="true"),
                     B(_("hub.worlds.title")),
                     Div(*[A(Span(lucide(w["icon"]), cls="dot", aria_hidden="true"),
                             Div(B(w["label"]), Span(_(f"hub.tour.{w['key']}"))),
                             href=w["href"], cls=f"mini-world w-{w['key']}") for w in worlds],
                         cls="mini-worlds"),
                     cls="disc-card") if len(worlds) > 1 else ""
    step_card = ""
    if other_step:
        tone = WORLD_TONES.get(other_step["world"], "")
        k = f"hub.step.{other_step['key']}"
        step_card = A(Span(lucide(other_step["icon"]), cls="ico", aria_hidden="true"),
                      Span(_("hub.next_in").format(world=_(f"nav.world_{other_step['world']}")), cls="cj-eyebrow",
                           style="color:var(--tone);"),
                      B(_(f"{k}.title")), P(_(f"{k}.text")),
                      Span(_(f"{k}.cta"), lucide("arrow-right"), cls="go"),
                      href=other_step["href"], cls="disc-card" + (f" t-{tone}" if tone else ""))
    return Div(
        Div(Span(lucide("compass"), cls="sec-ico lead", aria_hidden="true"), H2(_("hub.discover_title")),
            P(_("hub.discover_text")), cls="sec-h"),
        Div(learn, world_card, step_card, cls="disc"),
        cls="hub-sec", id="discover",
    )
