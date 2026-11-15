# features/help/content.py — the in-app guides, as data.
#
# Each guide is short (3 to 5 steps) and points to its full page on the
# MkDocs site (docs/docs/<docs_page>.md). Every text is an i18n key in
# i18n.py `_HELP_STRINGS`:
#   help.<slug>.title   the guide's title
#   help.<slug>.sum     one line under it
#   help.<slug>.s<N>t   step N's short title
#   help.<slug>.s<N>    step N's one sentence
#
# `paths` are the app paths the guide documents, for the "How this page
# works" entry of the "?" button. A pattern is a path prefix; "*" stands for
# one path segment (an id), and a trailing "$" means "this exact path".
# The longest pattern that matches wins.
#
# `audience` says who sees the guide (see audiences_for):
#   applicant       a new engineer still doing the welcome quests
#   everyone        any signed-in account past the welcome quests
#   clinic          the clinic side: clinic accounts and engineers
#   clinic_account  clinic accounts only (clinic setup)
#   engineer        engineers past the welcome quests
#   lead            team members who validate claims (/lead)
#   host            talk hosts (/host)
#   public          signed-out visitors (QR pages, library)

import os
from dataclasses import dataclass

from components import current_user_ctx, user_worlds, world_for_path

DEFAULT_DOCS_URL = "https://fixmymedtech.github.io/fixmymedtech-app/"
WORLD_ORDER = ("equipment", "work", "community")


@dataclass(frozen=True)
class Guide:
    slug: str
    world: str                  # equipment / work / community
    icon: str                   # a LUCIDE_ICONS name
    audience: tuple
    steps: tuple                # one href (or "") per step
    paths: tuple = ()
    docs_page: str = ""
    video_env: str = ""         # defaults to HELP_VIDEO_<SLUG>

    @property
    def key(self) -> str:
        return f"help.{self.slug}"

    def video_var(self) -> str:
        return self.video_env or "HELP_VIDEO_" + self.slug.upper().replace("-", "_")


GUIDES = (
    # ── How the app works ───────────────────────────────────
    Guide("three-worlds", "community", "layers", ("applicant", "everyone"),
          ("/dashboard", "/tasks", "/community", "", ""),
          paths=("/home$",), docs_page="three-worlds"),
    Guide("getting-started", "community", "flag", ("applicant", "engineer"),
          ("/community/start", "/community/start/quests", "/community/start/quests",
           "/community/start/quests", ""),
          paths=("/community/start", "/community/welcome", "/getting-started"),
          docs_page="start-engineer"),

    # ── Equipment ───────────────────────────────────────────
    Guide("register-device", "equipment", "qr", ("clinic",),
          ("/new_device", "", "", "", ""),
          paths=("/new_device", "/scan-result", "/device/*/new"),
          docs_page="register-device"),
    Guide("report-fault", "equipment", "faults", ("clinic", "public"),
          ("", "/faults", "", "", ""),
          paths=("/d/*", "/d/*/report", "/d/*/fault", "/faults", "/device/*/fault"),
          docs_page="report-fault"),
    Guide("clinic-devices", "equipment", "dashboard", ("clinic",),
          ("/dashboard", "/dashboard", "/devices", "", ""),
          paths=("/dashboard", "/devices", "/device/*"),
          docs_page="clinic-devices"),
    Guide("call-engineer", "equipment", "phone", ("clinic",),
          ("/devices", "", "", "", ""),
          paths=("/d/*/call", "/calls"),
          docs_page="call-engineer"),
    Guide("clinic-setup", "equipment", "groups", ("clinic_account",),
          ("/clinic/setup", "", "/groups", "", "/groups"),
          paths=("/clinic", "/groups/*/engineers", "/groups/*/privacy"),
          docs_page="start-clinic"),
    Guide("groups", "equipment", "users", ("clinic",),
          ("/groups", "/groups", "", ""),
          paths=("/groups",), docs_page="start-clinic"),
    Guide("manual-library", "equipment", "library", ("applicant", "everyone", "public"),
          ("/library", "", "", ""),
          paths=("/library", "/documents"), docs_page="attach-manual"),
    Guide("attach-manual", "equipment", "file-up", ("clinic",),
          ("/devices", "", "", ""),
          paths=("/devices/*/edit", "/device/*/documents"), docs_page="attach-manual"),

    # ── Work ────────────────────────────────────────────────
    Guide("my-work", "work", "tasks", ("engineer",),
          ("/tasks", "/community/tasks", "/tasks", ""),
          paths=("/tasks",), docs_page="engineer-workspace"),
    Guide("requests-offers", "work", "inbox", ("engineer",),
          ("/requests", "", "", ""),
          paths=("/requests",), docs_page="call-engineer"),
    Guide("invite-clinic", "work", "mail", ("engineer",),
          ("/invite-clinic", "", "/invite-clinic", "/new_device"),
          paths=("/invite-clinic",), docs_page="start-engineer"),
    Guide("talk-host", "work", "mic", ("host",),
          ("/host", "", "/host", ""),
          paths=("/host",), docs_page="start-lead"),

    # ── Community ───────────────────────────────────────────
    Guide("journey", "community", "hexagon", ("engineer",),
          ("/community", "/community/achievements", "/community/achievements", "/community/claims"),
          paths=("/community$", "/community/achievements", "/community/tree", "/community/roles"),
          docs_page="community-guide"),
    Guide("claims", "community", "award", ("engineer",),
          ("/community/claims", "", "", ""),
          paths=("/community/claims",), docs_page="community-work"),
    Guide("task-board", "community", "board", ("engineer",),
          ("/community/tasks", "", "", "/library"),
          paths=("/community/tasks",), docs_page="community-work"),
    Guide("validate-claims", "community", "check", ("lead",),
          ("/lead", "", "", "/lead"),
          paths=("/lead",), docs_page="community-work"),
    Guide("network", "community", "network", ("everyone",),
          ("/network", "/network", ""),
          paths=("/network", "/profile/*"), docs_page="community-guide"),
    Guide("profile", "community", "profile", ("everyone",),
          ("/profile", "/profile", "/profile", "/profile"),
          paths=("/profile$",), docs_page="start-engineer"),
)

BY_SLUG = {g.slug: g for g in GUIDES}


# ── Who sees what ───────────────────────────────────────────

def audiences_for(user: dict | None = None) -> set:
    """The audience tags this account belongs to."""
    user = user if user is not None else current_user_ctx()
    if not (user.get("name") or user.get("username") or user.get("email")):
        return {"public"}
    status = user.get("member_status") or "member"
    if status in ("applicant", "refused"):
        return {"applicant"}
    out = {"everyone", "clinic"}
    if (user.get("account_kind") or "engineer") == "engineer":
        out.add("engineer")
    else:
        out.add("clinic_account")
    perms = user.get("permissions") or []
    if any(str(p).startswith("recognise:") for p in perms):
        out.add("lead")
    if user.get("is_talk_host"):
        out.add("host")
    return out


def visible(guide: Guide, user: dict | None = None) -> bool:
    return bool(set(guide.audience) & audiences_for(user))


def guides_for(user: dict | None = None) -> list:
    aud = audiences_for(user)
    return [g for g in GUIDES if set(g.audience) & aud]


def grouped_for(user: dict | None = None) -> list:
    """[(world, [guides])] in world order, empty worlds left out."""
    aud = audiences_for(user)
    mine = guides_for(user)
    # A new engineer lives in the Community world: show it first.
    order = ("community", "equipment", "work") if "applicant" in aud else WORLD_ORDER
    return [(w, [g for g in mine if g.world == w]) for w in order
            if any(g.world == w for g in mine)]


def href_open(href: str, user: dict | None = None) -> bool:
    """Whether a "Go there" link leads somewhere this account can open
    (applicants would be bounced to /community/start)."""
    if not href:
        return False
    user = user if user is not None else current_user_ctx()
    status = user.get("member_status") or "member"
    if status in ("applicant", "refused"):
        from features.auth.helper import applicant_allowed
        return applicant_allowed(href)
    worlds = user_worlds("en", user)
    for w in worlds:
        for link, _icon, _label in w["links"]:
            if href == link or href.startswith(link.rstrip("/") + "/"):
                return True
    world = world_for_path(href)
    return world == "" or world in {w["key"] for w in worlds}


# ── Contextual help: which guide documents this path ────────

def _match(pattern: str, path: str) -> int:
    """Score of `pattern` for `path` (0 = no match). More segments score
    higher; a literal segment beats a "*"."""
    exact = pattern.endswith("$")
    pat = [s for s in pattern.rstrip("$").split("/") if s]
    seg = [s for s in path.split("/") if s]
    if len(seg) < len(pat) or (exact and len(seg) != len(pat)):
        return 0
    score = 0
    for p, s in zip(pat, seg):
        if p == "*":
            score += 1
        elif p == s:
            score += 2
        else:
            return 0
    return score + 1


def guide_for_path(path: str, user: dict | None = None):
    """The guide that best documents `path` for this account, or None."""
    best, best_score = None, 0
    for g in guides_for(user):
        for pattern in g.paths:
            score = _match(pattern, path or "")
            if score > best_score:
                best, best_score = g, score
    return best


# ── Links out ───────────────────────────────────────────────

def docs_url(guide: Guide) -> str:
    base = (os.getenv("DOCS_URL") or DEFAULT_DOCS_URL).strip()
    if not base.endswith("/"):
        base += "/"
    return f"{base}{guide.docs_page}/" if guide.docs_page else base


def video_url(guide: Guide) -> str:
    """The guide's video link from HELP_VIDEO_<SLUG>, or "" when unset.
    Only http(s) links are used."""
    url = (os.getenv(guide.video_var()) or "").strip()
    return url if url.startswith(("https://", "http://")) else ""
