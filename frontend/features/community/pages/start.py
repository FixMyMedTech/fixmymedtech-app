# /community/start — the applicant's home: the five welcome quests.
#
# Every platform page redirects an applicant here (features/auth/helper.py).
# Quests: complete your profile, watch the intro video, meet a member of the
# community (the host confirms it), join the Discord, answer the social media
# consent. When the last one is done the person becomes Ambassador and the
# platform opens (/community/welcome is shown once).
#
# Clinic staff invited by a clinic only need the video to get in; the same
# page then shows the other quests as the way to more features.

import httpx
from fasthtml.common import *
from starlette.responses import RedirectResponse

import features.auth.helper as auth_helper
import features.community.api as community_api
import features.profile.api as profile_api
from components import page_shell
from features.community.ui import (
    hero, check_mark, progress_bar, intro_video, country_select, flash, refresh_session, error_detail,
)
from i18n import t as make_t

rt = APIRouter()


def _quest(key, done, _, *body):
    return Div(
        check_mark(done),
        Div(
            Div(Span(_(f"cj.quest.{key}"), cls="cj-quest-title"),
                Span(_("cj.done") if done else _("cj.todo"), cls="badge " + ("badge-ok" if done else "badge-neutral")),
                cls="cj-between"),
            P(_(f"cj.quest.{key}.help")),
            *body,
            cls="cj-quest-body",
        ),
        cls="cj-quest" + (" done" if done else ""),
        id=f"quest-{key}",
    )


def _story_form(me, _):
    s = me.get("story") or {}
    return Form(
        Div(
            Div(Label(_("cj.story.photo"), cls="label", for_="avatar"),
                Input(type="file", id="avatar", name="avatar", accept="image/*", cls="input"),
                Span(_("cj.story.photo_ok") if s.get("has_photo") else _("cj.story.photo_missing"), cls="cj-small"),
                cls="form-group"),
            Div(Label(_("cj.join.country"), cls="label", for_="country"),
                country_select("country", s.get("country") or "", _), cls="form-group"),
            cls="form-row",
        ),
        Div(
            Div(Label(_("cj.join.city"), cls="label", for_="city"),
                Input(id="city", name="city", cls="input", value=s.get("city") or ""), cls="form-group"),
            Div(Label(_("cj.join.country_trained"), cls="label", for_="country_trained"),
                country_select("country_trained", s.get("country_trained") or "", _), cls="form-group"),
            cls="form-row",
        ),
        Div(Label(_("cj.story.why_bme"), cls="label", for_="why_bme"),
            Textarea(s.get("why_bme") or "", id="why_bme", name="why_bme", rows="3", maxlength="500", cls="input",
                     placeholder=_("cj.story.why_bme_placeholder")),
            cls="form-group"),
        Button(_("cj.story.save"), type="submit", cls="btn btn-primary btn-sm"),
        method="post", action="/community/start/story", enctype="multipart/form-data",
    )


def _meeting_body(me, _):
    app = me.get("application") or {}
    cfg = me.get("config") or {}
    parts = []
    if app.get("meeting_at"):
        when = app["meeting_at"].replace("T", " ")[:16]
        host = app.get("host_name")
        parts.append(P(_("cj.meeting.booked").format(when=when) + (" " + _("cj.meeting.with").format(host=host) if host else ""),
                       style="color:var(--text);"))
    if cfg.get("booking_url"):
        parts.append(A(_("cj.meeting.book"), href=cfg["booking_url"], target="_blank", rel="noopener",
                       cls="btn btn-primary btn-sm", style="align-self:flex-start;"))
    else:
        parts.append(P(_("cj.meeting.no_link")))
    return parts


def _discord_body(me, _):
    cfg = me.get("config") or {}
    parts = [Div(
        A(_("cj.discord.connect"), href="/profile/discord/connect", cls="btn btn-primary btn-sm"),
        A(_("cj.discord.open"), href=cfg["discord_invite_url"], target="_blank", rel="noopener",
          cls="btn btn-secondary btn-sm") if cfg.get("discord_invite_url") else "",
        cls="cj-row")]
    parts.append(Span(_("cj.discord.host_can_confirm"), cls="cj-small"))
    return parts


def _consent_body(me, _):
    current = me.get("social_consent")
    return [
        Div(Span(_("cj.consent.example_label"), cls="cj-small"),
            P(_("cj.consent.example"), style="color:var(--text);"),
            style="border:1px solid var(--border);border-radius:var(--radius-control);padding:12px;background:var(--sunken);"),
        Form(
            Fieldset(
                Legend(_("cj.consent.answer"), cls="label"),
                Label(Input(type="radio", name="social", value="yes", checked=current is True), _("cj.consent.yes"),
                      cls="cj-choice"),
                Label(Input(type="radio", name="social", value="no", checked=current is False), _("cj.consent.no"),
                      cls="cj-choice"),
                style="border:0;margin:0;padding:0;display:flex;flex-direction:column;gap:8px;",
            ),
            Button(_("cj.consent.save"), type="submit", cls="btn btn-primary btn-sm", style="margin-top:8px;"),
            method="post", action="/community/start/consent",
        ),
        Span(_("cj.consent.change_later"), cls="cj-small"),
    ]


def _page(me, _, lang, notice=None):
    quests = {q["key"]: q["done"] for q in me.get("welcome_quests") or []}
    done = sum(1 for v in quests.values() if v)
    total = len(quests) or 5
    status = me.get("member_status")
    staff = status == "staff"
    cfg = me.get("config") or {}
    video_url = cfg.get("staff_intro_video_url") if me.get("join_path") == "clinic_staff" else cfg.get("intro_video_url")
    first = (me.get("full_name") or "").split(" ")[0]

    if status == "refused":
        reason = (me.get("application") or {}).get("decision_reason")
        return Div(
            hero(_("cj.refused.title"), _("cj.refused.text")),
            Div(H3(_("cj.refused.reason")), P(reason or "—"), P(_("cj.refused.contact")), cls="cj-card"),
            cls="cj cj-narrow",
        )

    if status == "member":
        top = hero(_("cj.start.member_title"), _("cj.start.member_text"), _("cj.start.eyebrow"))
    elif staff:
        top = hero(_("cj.start.staff_title"), _("cj.start.staff_text"), _("cj.start.eyebrow"))
    else:
        top = hero(_("cj.start.title").format(name=first), _("cj.start.text"), _("cj.start.eyebrow"))

    return Div(
        top,
        notice or "",
        Div(
            Div(H2(_("cj.start.quests")), Span(_("cj.start.progress").format(done=done, total=total), cls="cj-small"),
                cls="cj-between"),
            progress_bar(done, total, _("cj.start.progress").format(done=done, total=total)),
            _quest("profile_complete", quests.get("profile_complete"), _, _story_form(me, _)),
            _quest("intro_video", quests.get("intro_video"), _, intro_video(video_url, quests.get("intro_video"), _)),
            _quest("meeting_held", quests.get("meeting_held"), _, *_meeting_body(me, _)),
            _quest("discord_joined", quests.get("discord_joined"), _, *([] if quests.get("discord_joined") else _discord_body(me, _))),
            _quest("consent_answered", quests.get("consent_answered"), _, *_consent_body(me, _)),
            cls="cj-card",
        ),
        Div(
            H3(_("cj.start.tree_title")),
            P(_("cj.start.tree_text")),
            A(_("cj.start.tree_link"), href="/community/tree", cls="btn btn-secondary btn-sm", style="align-self:flex-start;"),
            cls="cj-card",
        ),
        A(_("cj.start.go_platform"), href="/home", cls="btn btn-primary", style="align-self:flex-start;")
        if status in ("member", "staff") else "",
        cls="cj cj-narrow",
    )


async def _render(req, token, notice=None):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    try:
        me = await community_api.get_me(token)
    except Exception:
        return page_shell(Div(flash(_("cj.error.load"), "error"), cls="cj"), current="/community/start",
                          title=_("cj.title.start"), lang=lang)
    if me.get("member_status") != req.session.get("member_status"):
        await refresh_session(req, token)
    if req.session.pop("show_welcome", None):
        return RedirectResponse("/community/welcome", status_code=302)
    return page_shell(_page(me, _, lang, notice), current="/community/start", title=_("cj.title.start"), lang=lang)


@rt("/community/start")
async def get(req, joined: str = "", saved: str = "", err: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    _ = make_t(req.session.get("lang", "en"))
    notice = None
    if joined:
        notice = flash(_("cj.start.joined"))
    elif saved:
        notice = flash(_("cj.saved"))
    elif err:
        notice = flash(_("cj.error.save"), "error")
    return await _render(req, token, notice)


async def _after_change(req, token, ok=True):
    await refresh_session(req, token)
    if req.session.pop("show_welcome", None):
        return RedirectResponse("/community/welcome", status_code=303)
    return RedirectResponse("/community/start?" + ("saved=1" if ok else "err=1"), status_code=303)


@rt("/community/start/story")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    ok = True
    avatar = form.get("avatar")
    if avatar is not None and getattr(avatar, "filename", ""):
        try:
            content = await avatar.read()
            if content:
                await profile_api.upload_avatar(token, avatar.filename or "avatar.jpg", content,
                                                getattr(avatar, "content_type", None))
                req.session.pop("user_avatar", None)
        except Exception:
            ok = False
    try:
        await community_api.update_story(token, {
            k: (form.get(k) or "").strip() for k in ("country", "city", "country_trained", "why_bme")
        })
    except Exception:
        ok = False
    return await _after_change(req, token, ok)


@rt("/community/start/video")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await community_api.intro_video_watched(token)
        ok = True
    except Exception:
        ok = False
    return await _after_change(req, token, ok)


@rt("/community/start/consent")
async def post(req):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    answer = form.get("social")
    if answer not in ("yes", "no"):
        return RedirectResponse("/community/start?err=1#quest-consent_answered", status_code=303)
    try:
        await community_api.set_consent(token, answer == "yes")
        ok = True
    except Exception:
        ok = False
    return await _after_change(req, token, ok)
