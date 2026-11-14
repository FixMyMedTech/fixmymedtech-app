# features/community/pages/work.py — wave 5, the community's own work.
#
#   /lead               leader portal: claims to validate, tasks to check,
#                       shortcuts to talks (/host) and team admin
#   /community/claims   claim a recognised achievement, see my claims
#   /community/tasks    the task board: take, finish, check; points
#   /community/tasks/find-manual   "Find this manual" (device card, library)
#
# Rules live in the backend (routers/community_work.py): a team lead or a
# superuser confirms a claim alone, otherwise two team members must agree;
# the author of a task or a lead checks it, never the one who did it.

from urllib.parse import quote

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse, Response

import features.auth.helper as auth_helper
import features.community.api as community_api
from components import page_shell, fmt_date, page_head
from features.community.ui import flash, error_detail, perms, has_dashboard, name_of
from i18n import t as make_t

rt = APIRouter()

WORK_CSS = """
.work{max-width:860px;}
.work .lead-in{color:var(--text-muted);margin:-4px 0 16px;}
.work .muted{color:var(--text-muted);font-size:14px;}
.work .small{font-size:12px;color:var(--text-muted);}
.shortcuts{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:12px;margin-bottom:20px;}
.shortcut{display:block;padding:14px 16px;background:var(--surface);border:1px solid var(--border);border-top:3px solid var(--border-strong);border-radius:var(--radius-card);text-decoration:none;color:var(--text);}
.shortcut:hover{background:var(--sunken);}
.shortcut .num{font-size:24px;font-weight:700;line-height:1.2;font-variant-numeric:tabular-nums;}
.shortcut .lbl{font-size:14px;font-weight:600;}
.shortcut .sub{font-size:12px;color:var(--text-muted);}
.shortcut.is-warn{border-top-color:var(--warn);} .shortcut.is-warn .num{color:var(--warn);}
.shortcut.is-ok{border-top-color:var(--ok);} .shortcut.is-primary{border-top-color:var(--primary);}
.wcard{background:var(--surface);border:1px solid var(--border);border-left:4px solid var(--border-strong);border-radius:var(--radius-card);padding:14px 16px;margin-bottom:10px;}
.wcard.is-warn{border-left-color:var(--warn);} .wcard.is-ok{border-left-color:var(--ok);} .wcard.is-danger{border-left-color:var(--danger);} .wcard.is-primary{border-left-color:var(--primary);}
.wcard-top{display:flex;gap:12px;align-items:flex-start;}
.wcard-top .grow{flex:1;min-width:0;}
.wcard h4{margin:0 0 2px;font-size:16px;line-height:1.3;}
.wcard .quote{margin:8px 0 0;padding:8px 12px;background:var(--sunken);border-radius:var(--radius-control);font-size:14px;color:var(--text);white-space:pre-wrap;}
.wcard .proof{width:96px;height:96px;object-fit:cover;border-radius:var(--radius-control);border:1px solid var(--border);flex-shrink:0;}
.wactions{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:12px;}
.wactions form{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin:0;}
.wactions input[type=text]{min-width:180px;flex:1;}
.votes{display:inline-flex;gap:4px;align-items:center;font-size:12px;color:var(--text-muted);}
.votes i{width:10px;height:10px;border-radius:50%;background:var(--sunken);border:1px solid var(--border-strong);display:inline-block;}
.votes i.on{background:var(--ok);border-color:var(--ok);}
.points{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between;padding:16px 18px;margin-bottom:16px;border-radius:var(--radius-card);background:var(--primary-tint);color:var(--text);}
.points .big{font-size:32px;font-weight:700;line-height:1;color:var(--primary);font-variant-numeric:tabular-nums;}
.board-leaders{list-style:none;margin:0;padding:0;display:flex;flex-wrap:wrap;gap:6px;}
.board-leaders li{font-size:12px;font-weight:600;padding:3px 10px;border-radius:var(--radius-pill);background:var(--surface);border:1px solid var(--border);}
.kind{display:inline-block;font-size:12px;font-weight:600;padding:1px 8px;border-radius:var(--radius-pill);background:var(--sunken);color:var(--text-muted);}
.pts{font-weight:700;font-size:14px;color:var(--primary);white-space:nowrap;font-variant-numeric:tabular-nums;}
.wsection{margin:22px 0 10px;font-size:16px;}
.wempty{padding:16px;border:1px dashed var(--border-strong);border-radius:var(--radius-card);color:var(--text-muted);font-size:14px;}
.wform .field{margin-bottom:12px;}
.wform label.lbl{display:block;font-size:12px;font-weight:600;color:var(--text-muted);margin-bottom:4px;}
"""

TASK_KINDS = ("find_manual", "verify_clinic", "fill_brand_list", "other")
STATUS_TONE = {"pending": "warn", "more_info": "danger", "confirmed": "ok", "declined": "neutral"}


def _shell(content, title, lang, current):
    return page_shell(Div(Style(WORK_CSS), content, cls="work"), current=current, title=title, lang=lang)


def _back(path: str, msg: str = "", error: str = ""):
    q = "&".join(f"{k}={quote(v)}" for k, v in (("msg", msg), ("error", error)) if v)
    path, hash_, frag = path.partition("#")
    sep = "&" if "?" in path else "?"
    return RedirectResponse((f"{path}{sep}{q}" if q else path) + hash_ + frag, status_code=303)


def _auth(req):
    token, redirect = auth_helper.require_auth(req)
    lang = req.session.get("lang", "en")
    return token, redirect, lang, make_t(lang)


def _expired(req, e):
    if isinstance(e, httpx.HTTPStatusError) and e.response.status_code == 401:
        auth_helper.clear_session(req)
        return RedirectResponse("/login?expired=1", status_code=302)
    return None


def _ach_name(c: dict, lang: str) -> str:
    names = c.get("achievement_names") or {}
    return names.get(lang) or names.get("en") or c.get("achievement_key", "")


def _votes(c: dict, _):
    n, need = len(c.get("confirmed_by") or []), c.get("needed") or 2
    return Span(*[I(cls="on" if i < n else "") for i in range(need)],
                Span(_("w5.votes").format(n=n, need=need)), cls="votes")


# ══════════════════════════════════════════════════════════════
# LEADER PORTAL
# ══════════════════════════════════════════════════════════════

@rt("/lead", methods=["get"])
async def lead(req, msg: str = "", error: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        review = await community_api.claims_to_review(token)
        board = await community_api.task_board(token)
    except Exception as e:
        return _expired(req, e) or RedirectResponse("/community", status_code=302)
    claims = review.get("claims") or []
    to_check = board.get("to_check") or []
    user_hosts = bool(req.session.get("user_is_talk_host"))

    def claim_card(c):
        lead_here = c.get("is_lead_here")
        tone = "danger" if c.get("status") == "more_info" else "warn"
        confirm_label = _("w5.confirm") if lead_here else (
            _("w5.confirm_vote_done") if c.get("i_confirmed") else _("w5.confirm_vote"))
        return Div(
            Div(
                Div(
                    Div(_("w5.claim_eyebrow").format(team=_(f"w5.team.{c.get('team_key')}", c.get("team_key") or "")),
                        cls="eyebrow"),
                    H4(_("w5.claim_line").format(who=c.get("claimant") or "?", what=_ach_name(c, lang),
                                                 n=c.get("count") or 1)),
                    Div(fmt_date(c.get("created_at") or ""), " · ", _votes(c, _), cls="small"),
                    P(c.get("note") or "", cls="quote"),
                    P(_("w5.asked").format(note=c.get("review_note")), cls="small", style="margin-top:6px;")
                    if c.get("status") == "more_info" and c.get("review_note") else "",
                    cls="grow"),
                A(Img(src=f"/community/claims/{c['id']}/proof", alt=_("w5.proof"), cls="proof"),
                  href=f"/community/claims/{c['id']}/proof", target="_blank", rel="noopener")
                if c.get("has_proof") else "",
                cls="wcard-top"),
            Div(
                Form(Button(confirm_label, type="submit", cls="btn btn-primary btn-sm",
                            disabled=bool(c.get("i_confirmed") and not lead_here)),
                     method="post", action=f"/lead/claims/{c['id']}/confirm"),
                Form(Input(type="text", name="note", cls="input", placeholder=_("w5.note_placeholder"),
                           aria_label=_("w5.note_placeholder")),
                     Button(_("w5.ask_more"), type="submit", name="act", value="more", cls="btn btn-secondary btn-sm"),
                     Button(_("w5.decline"), type="submit", name="act", value="decline", cls="btn btn-secondary btn-sm"),
                     method="post", action=f"/lead/claims/{c['id']}/review"),
                cls="wactions"),
            cls=f"wcard is-{tone}",
        )

    def check_card(tk):
        return Div(
            Div(Div(Span(_(f"w5.kind.{tk.get('kind')}"), cls="kind"), H4(tk.get("title", ""), style="margin-top:6px;"),
                    Div(_("w5.done_by").format(who=tk.get("taker") or "?", date=fmt_date(tk.get("done_at") or "")),
                        cls="small"),
                    P(tk.get("done_note") or "", cls="quote"), cls="grow"),
                Span(f"+{tk.get('points', 0)}", cls="pts"), cls="wcard-top"),
            Div(Form(Button(_("w5.check_ok"), type="submit", cls="btn btn-primary btn-sm"),
                     method="post", action=f"/community/tasks/{tk['id']}/check?back=/lead"),
                Form(Button(_("w5.send_back"), type="submit", cls="btn btn-secondary btn-sm"),
                     method="post", action=f"/community/tasks/{tk['id']}/send-back?back=/lead"),
                cls="wactions"),
            cls="wcard is-primary",
        )

    def shortcut(num, label, sub, href, tone):
        return A(Div(num, cls="num"), Div(label, cls="lbl"), Div(sub, cls="sub"), href=href, cls=f"shortcut is-{tone}")

    shortcuts = [
        shortcut(str(len(claims)), _("w5.sc_claims"), _("w5.sc_claims_sub"), "#claims", "warn" if claims else "ok"),
        shortcut(str(len(to_check)), _("w5.sc_tasks"), _("w5.sc_tasks_sub"), "#check", "warn" if to_check else "ok"),
    ]
    if user_hosts:
        shortcut_host = shortcut("🎙", _("w5.sc_host"), _("w5.sc_host_sub"), "/host", "primary")
        shortcuts.append(shortcut_host)
    if has_dashboard(req):
        shortcuts.append(shortcut("⚙", _("w5.sc_admin"), _("w5.sc_admin_sub"), "/community/admin", "primary"))
    shortcuts.append(shortcut("✚", _("w5.sc_board"), _("w5.sc_board_sub"), "/community/tasks", "primary"))

    content = Div(
        page_head(_("w5.lead_title"), _("w5.lead_intro"), "check", "lead"),
        flash(msg), flash(error, "error"),
        Div(*shortcuts, cls="shortcuts"),
        H3(_("w5.claims_title"), cls="wsection", id="claims"),
        *([claim_card(c) for c in claims] or
          [Div(_("w5.claims_none") if review.get("can_review") else _("w5.claims_not_yours"), cls="wempty")]),
        H3(_("w5.check_title"), cls="wsection", id="check"),
        *([check_card(tk) for tk in to_check] or [Div(_("w5.check_none"), cls="wempty")]),
    )
    return _shell(content, _("w5.lead_title"), lang, "/lead")


@rt("/lead/claims/{claim_id}/confirm", methods=["post"])
async def lead_confirm(req, claim_id: str):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        r = await community_api.review_claim(token, claim_id, "confirm")
    except Exception as e:
        return _expired(req, e) or _back("/lead", error=error_detail(e))
    return _back("/lead", msg=_("w5.confirmed") if r.get("status") == "confirmed" else _("w5.vote_counted"))


@rt("/lead/claims/{claim_id}/review", methods=["post"])
async def lead_review(req, claim_id: str, act: str = "more", note: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    act = "decline" if act == "decline" else "more"
    try:
        await community_api.review_claim(token, claim_id, act, note.strip())
    except Exception as e:
        return _expired(req, e) or _back("/lead", error=error_detail(e))
    return _back("/lead", msg=_("w5.declined") if act == "decline" else _("w5.asked_more"))


@rt("/community/claims/{claim_id}/proof", methods=["get"])
async def claim_proof(req, claim_id: str):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        content, ctype = await community_api.get_claim_proof(token, claim_id)
    except Exception:
        return Response(status_code=404)
    return Response(content=content, media_type=ctype)


# ══════════════════════════════════════════════════════════════
# CLAIM AN ACHIEVEMENT
# ══════════════════════════════════════════════════════════════

@rt("/community/claims", methods=["get"])
async def claims_page(req, msg: str = "", error: str = "", key: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        options = await community_api.claim_options(token)
        mine = await community_api.my_claims(token)
    except Exception as e:
        return _expired(req, e) or RedirectResponse("/community", status_code=302)
    is_member = req.session.get("member_status", "member") == "member"

    def option(o):
        team = o.get("team_key") or ""
        return Option(f"{name_of(o, lang)} · {_('w5.team.' + team, team)}",
                      value=o["key"], selected=(o["key"] == key))

    form = Div(
        H3(_("w5.claim_form_title"), cls="card-title"),
        P(_("w5.claim_form_intro"), cls="muted"),
        Form(
            Div(Label(_("w5.claim_what"), cls="lbl", fr="ach"),
                Select(*[option(o) for o in options], name="achievement_key", id="ach", cls="input", required=True),
                cls="field"),
            Div(Label(_("w5.claim_count"), cls="lbl", fr="cnt"),
                Input(type="number", name="count", id="cnt", value="1", min="1", max="100", cls="input",
                      style="max-width:120px;", inputmode="numeric"), cls="field"),
            Div(Label(_("w5.claim_note"), cls="lbl", fr="note"),
                Textarea(name="note", id="note", rows="3", cls="input", required=True, minlength="3",
                         placeholder=_("w5.claim_note_ph")), cls="field"),
            Div(Label(_("w5.claim_photo"), cls="lbl", fr="photo"),
                Input(type="file", name="photo", id="photo", accept="image/*", cls="input"), cls="field"),
            Button(_("w5.claim_send"), type="submit", cls="btn btn-primary"),
            method="post", action="/community/claims", enctype="multipart/form-data", cls="wform",
        ) if is_member else P(_("w5.claim_members_only"), cls="wempty"),
        cls="card", style="margin-bottom:16px;",
    )

    def mine_card(c):
        st = c.get("status") or "pending"
        extra = ""
        if st == "more_info":
            extra = Div(
                P(_("w5.they_ask").format(who=c.get("reviewer") or "", note=c.get("review_note") or ""),
                  cls="small", style="margin-top:8px;color:var(--danger);font-weight:600;"),
                Form(Textarea(c.get("note") or "", name="note", rows="3", cls="input", required=True),
                     Input(type="file", name="photo", accept="image/*", cls="input"),
                     Button(_("w5.claim_resend"), type="submit", cls="btn btn-primary btn-sm"),
                     method="post", action=f"/community/claims/{c['id']}/answer", enctype="multipart/form-data",
                     style="display:grid;gap:8px;margin-top:8px;"),
            )
        elif st == "declined" and c.get("review_note"):
            extra = P(_("w5.declined_why").format(note=c.get("review_note")), cls="small", style="margin-top:6px;")
        return Div(
            Div(Div(H4(_("w5.my_claim_line").format(what=_ach_name(c, lang), n=c.get("count") or 1)),
                    Div(fmt_date(c.get("created_at") or ""), " · ", _(f"w5.status.{st}"),
                        *([" · ", _votes(c, _)] if st == "pending" else []), cls="small"),
                    cls="grow"),
                cls="wcard-top"),
            extra,
            cls=f"wcard is-{STATUS_TONE.get(st, 'warn')}",
        )

    content = Div(
        page_head(_("w5.claims_page_title"), _("w5.claims_page_intro"), "hexagon", "lead"),
        flash(msg), flash(error, "error"),
        form,
        H3(_("w5.my_claims"), cls="wsection"),
        *([mine_card(c) for c in mine] or [Div(_("w5.my_claims_none"), cls="wempty")]),
    )
    return _shell(content, _("w5.claims_page_title"), lang, "/community/achievements")


async def _photo(req):
    form = await req.form()
    up = form.get("photo")
    if up is not None and getattr(up, "filename", ""):
        content = await up.read()
        if content:
            return form, (up.filename, content, up.content_type)
    return form, None


@rt("/community/claims", methods=["post"])
async def claims_post(req):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    form, photo = await _photo(req)
    try:
        count = int(form.get("count") or 1)
    except ValueError:
        count = 1
    try:
        r = await community_api.make_claim(token, {"achievement_key": form.get("achievement_key") or "",
                                                   "count": count, "note": (form.get("note") or "").strip()})
        if photo:
            await community_api.add_claim_proof(token, r["id"], *photo)
    except Exception as e:
        return _expired(req, e) or _back("/community/claims", error=error_detail(e))
    return _back("/community/claims", msg=_("w5.claim_sent"))


@rt("/community/claims/{claim_id}/answer", methods=["post"])
async def claims_answer(req, claim_id: str):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    form, photo = await _photo(req)
    try:
        await community_api.answer_claim(token, claim_id, (form.get("note") or "").strip())
        if photo:
            await community_api.add_claim_proof(token, claim_id, *photo)
    except Exception as e:
        return _expired(req, e) or _back("/community/claims", error=error_detail(e))
    return _back("/community/claims", msg=_("w5.claim_sent"))


# ══════════════════════════════════════════════════════════════
# TASK BOARD
# ══════════════════════════════════════════════════════════════

@rt("/community/tasks", methods=["get"])
async def task_board(req, msg: str = "", error: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        b = await community_api.task_board(token)
    except Exception as e:
        return _expired(req, e) or RedirectResponse("/community", status_code=302)

    def ref_link(tk):
        if tk.get("ref_device_id"):
            return A(_("w5.see_device"), href=f"/device/{tk['ref_device_id']}", cls="small")
        if tk.get("kind") == "find_manual" and tk.get("ref_model"):
            q = " ".join(x for x in (tk.get("ref_manufacturer"), tk.get("ref_model")) if x)
            return A(_("w5.search_library"), href=f"/library?q={quote(q)}", cls="small")
        return ""

    def card(tk, mode):
        tone = {"mine": "primary", "open": "warn", "done": "ok"}.get(mode, "warn")
        who = ""
        if mode == "done":
            who = _("w5.done_by").format(who=tk.get("taker") or "?", date=fmt_date(tk.get("checked_at") or tk.get("done_at") or ""))
        elif mode == "open":
            who = _("w5.posted_by").format(who=tk.get("creator") or "?")
        actions = []
        tid = tk["id"]
        if mode == "open" and b.get("can_take"):
            actions.append(Form(Button(_("w5.take"), type="submit", cls="btn btn-primary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/take"))
        if mode == "open" and tk.get("can_cancel"):
            actions.append(Form(Button(_("w5.cancel_task"), type="submit", cls="btn btn-secondary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/cancel"))
        if mode == "mine" and tk.get("status") == "taken":
            actions.append(Form(Input(type="text", name="note", cls="input", required=True, minlength="3",
                                      placeholder=_("w5.done_ph"), aria_label=_("w5.done_ph")),
                                Button(_("w5.mark_done"), type="submit", cls="btn btn-primary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/done"))
            actions.append(Form(Button(_("w5.drop"), type="submit", cls="btn btn-secondary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/drop"))
        if mode == "mine" and tk.get("status") == "review":
            actions.append(Span(_("w5.waiting_check"), cls="small"))
        if mode == "check":
            actions.append(Form(Button(_("w5.check_ok"), type="submit", cls="btn btn-primary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/check"))
            actions.append(Form(Button(_("w5.send_back"), type="submit", cls="btn btn-secondary btn-sm"),
                                method="post", action=f"/community/tasks/{tid}/send-back"))
        return Div(
            Div(Div(Span(_(f"w5.kind.{tk.get('kind')}"), cls="kind"),
                    H4(tk.get("title", ""), style="margin-top:6px;"),
                    P(tk.get("details") or "", cls="small", style="margin:2px 0 0;") if tk.get("details") else "",
                    P(tk.get("done_note") or "", cls="quote") if mode in ("check", "done") and tk.get("done_note") else "",
                    Div(*[x for x in (who, ref_link(tk)) if x], cls="small", style="display:flex;gap:10px;flex-wrap:wrap;margin-top:4px;"),
                    cls="grow"),
                Span(f"+{tk.get('points', 0)}", cls="pts"), cls="wcard-top"),
            Div(*actions, cls="wactions") if actions else "",
            cls=f"wcard is-{tone}",
        )

    leaders = b.get("leaders") or []
    points = Div(
        Div(Div(str(b.get("my_points", 0)), cls="big"), Div(_("w5.my_points"), cls="small")),
        Div(Div(_("w5.leaders"), cls="eyebrow", style="margin-bottom:6px;"),
            Ul(*[Li(f"{i + 1}. {l['name']} · {l['points']}") for i, l in enumerate(leaders[:5])], cls="board-leaders")
            if leaders else Div(_("w5.leaders_none"), cls="small")),
        cls="points",
    )

    create = Details(
        Summary(_("w5.new_task")),
        Form(
            Div(Label(_("w5.task_kind"), cls="lbl", fr="kind"),
                Select(*[Option(_(f"w5.kind.{k}"), value=k) for k in TASK_KINDS], name="kind", id="kind", cls="input"),
                cls="field"),
            Div(Label(_("w5.task_title"), cls="lbl", fr="ttl"),
                Input(type="text", name="title", id="ttl", cls="input", required=True, minlength="3", maxlength="200"),
                cls="field"),
            Div(Label(_("w5.task_details"), cls="lbl", fr="det"),
                Textarea(name="details", id="det", rows="3", cls="input"), cls="field"),
            Div(Label(_("w5.task_points"), cls="lbl", fr="pts"),
                Input(type="number", name="points", id="pts", value="10", min="1", max="500", cls="input",
                      style="max-width:120px;"), cls="field"),
            Button(_("w5.post_task"), type="submit", cls="btn btn-primary"),
            method="post", action="/community/tasks", cls="wform card",
        ),
        cls="more",
    ) if b.get("can_create") else P(_("w5.tasks_members_only"), cls="wempty", style="margin-bottom:16px;")

    def section(title, items, mode, empty, anchor):
        return Div(H3(title, cls="wsection", id=anchor),
                   *([card(tk, mode) for tk in items] or [Div(empty, cls="wempty")]))

    content = Div(
        Style(".work details.more>summary{cursor:pointer;list-style:none;padding:14px 18px;background:var(--surface);"
              "border:1px solid var(--border);border-radius:var(--radius-card);font-weight:600;margin-bottom:12px;}"),
        page_head(_("w5.board_title"), _("w5.board_intro"), "board", "lead"),
        flash(msg), flash(error, "error"),
        points,
        create,
        section(_("w5.sec_mine"), b.get("mine") or [], "mine", _("w5.mine_none"), "mine"),
        section(_("w5.sec_check"), b.get("to_check") or [], "check", _("w5.check_none"), "check")
        if b.get("to_check") else "",
        section(_("w5.sec_open"), b.get("open") or [], "open", _("w5.open_none"), "open"),
        section(_("w5.sec_done"), b.get("done") or [], "done", _("w5.done_none"), "done"),
    )
    return _shell(content, _("w5.board_title"), lang, "/community/tasks")


@rt("/community/tasks", methods=["post"])
async def task_create(req, kind: str = "other", title: str = "", details: str = "", points: str = "10"):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    try:
        pts = max(1, min(500, int(points or 10)))
    except ValueError:
        pts = 10
    try:
        await community_api.create_task(token, {"kind": kind if kind in TASK_KINDS else "other",
                                                "title": title.strip(), "details": details.strip() or None,
                                                "points": pts})
    except Exception as e:
        return _expired(req, e) or _back("/community/tasks", error=error_detail(e))
    return _back("/community/tasks", msg=_("w5.task_posted"))


@rt("/community/tasks/find-manual", methods=["post"])
async def task_find_manual(req, manufacturer: str = "", model: str = "", device_id: str = "", back: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    back = back if back.startswith("/") and not back.startswith("//") else "/community/tasks"
    if not model.strip():
        return _back(back, error=_("w5.model_needed"))
    try:
        r = await community_api.find_manual(token, manufacturer.strip(), model.strip(), device_id or None)
    except Exception as e:
        return _expired(req, e) or _back(back, error=error_detail(e))
    return _back(back, msg=_("w5.manual_task_exists") if r.get("existing") else _("w5.manual_task_made"))


_TASK_MSG = {"take": "w5.taken", "done": "w5.sent_check", "check": "w5.checked", "send-back": "w5.sent_back",
             "drop": "w5.dropped", "cancel": "w5.cancelled"}


@rt("/community/tasks/{task_id}/{action}", methods=["post"])
async def task_act(req, task_id: str, action: str, note: str = "", back: str = ""):
    token, redirect, lang, _ = _auth(req)
    if redirect:
        return redirect
    back = back if back.startswith("/") and not back.startswith("//") else "/community/tasks"
    if action not in _TASK_MSG:
        return _back(back)
    try:
        await community_api.task_action(token, task_id, action, {"note": note.strip()} if action == "done" else {})
    except Exception as e:
        return _expired(req, e) or _back(back, error=error_detail(e))
    return _back(back, msg=_(_TASK_MSG[action]))
