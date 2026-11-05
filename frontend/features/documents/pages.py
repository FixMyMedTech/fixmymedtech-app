# pages.py — the public document library and the document actions used by the
# device edit page and device registration.
#
# Reading is public; attaching, uploading and removing need a logged-in user
# (the API enforces the same).

from urllib.parse import quote

from fasthtml.common import *
from starlette.responses import RedirectResponse, Response
import httpx

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.documents.api as docs_api

from components import pub_shell
from features.documents.components import (DOCS_CSS, TYPES, doc_list, ifixit_results,
                                           type_label, TYPE_ICONS)

rt = APIRouter()


def _back(device_id: str, **flash) -> RedirectResponse:
    q = "&".join(f"{k}={quote(str(v))}" for k, v in flash.items())
    return RedirectResponse(f"/devices/{device_id}/edit?{q}#documents", status_code=303)


def _error_text(e: Exception) -> str:
    return str(e) if isinstance(e, httpx.HTTPStatusError) and e.response.status_code < 500 else ""


async def attach_selected(token: str, device_id: str, values: list) -> int:
    """Attach the ticked "<documentid>|<page>" values. Returns how many worked."""
    ok = 0
    for v in values:
        doc_id, _sep, page = str(v).partition("|")
        if not doc_id.isdigit() or not page:
            continue
        try:
            await docs_api.attach_ifixit(token, device_id, page, int(doc_id))
            ok += 1
        except Exception:
            pass
    return ok


# ── library ──────────────────────────────────────────────────────────────────

@rt("/library")
async def get(req, q: str = "", type: str = ""):
    lang = req.session.get("lang", "en")
    _ = make_t(lang)
    q = q.strip()[:100]
    type = type if type in TYPES else ""

    try:
        ours = await docs_api.search_library(q, type)
    except Exception:
        ours = []
    ifx, ifx_error = [], ""
    if q:
        try:
            ifx = await docs_api.search_ifixit(q)
        except Exception:
            ifx_error = _("docs.ifixit_error")
    if type:
        ifx = [{**p, "documents": [d for d in p["documents"] if d["type"] == type]} for p in ifx]
        ifx = [p for p in ifx if p["documents"]]

    def our_item(d):
        n = d.get("devices") or 0
        extra = " · ".join(x for x in (d.get("manufacturer"), d.get("model")) if x)
        return Div(
            Span(TYPE_ICONS.get(d.get("type"), "📄"), cls="doc-ico"),
            Div(A(d["title"], href=d["url"], target="_blank", rel="noopener", cls="doc-title"),
                Div(" · ".join(x for x in (type_label(_, d.get("type")), extra,
                                           f"{n} {_('docs.used_by')}" if n else "") if x),
                    Span(_("docs.source_ifixit") if d.get("source") == "ifixit" else _("docs.source_upload"),
                         cls=f"doc-src {'ifixit' if d.get('source') == 'ifixit' else ''}"),
                    cls="doc-meta"),
                cls="doc-body"),
            cls="doc-item",
        )

    def ifx_page(p):
        return Div(
            Div(A(p["title"], href=p["url"], target="_blank", rel="noopener"), cls="ifx-page-title"),
            Div(*[Div(Span(TYPE_ICONS.get(d["type"], "📄"), cls="doc-ico"),
                      Div(A(d["title"], href=d["url"], target="_blank", rel="noopener", cls="doc-title"),
                          Div(" · ".join([type_label(_, d["type"])] + ([f"{d['pages']} {_('docs.pages')}"] if d.get("pages") else [])),
                              Span(_("docs.source_ifixit"), cls="doc-src ifixit"), cls="doc-meta"),
                          cls="doc-body"),
                      cls="doc-item") for d in p["documents"]], cls="doc-list"),
            cls="ifx-page", style="margin-bottom:14px;",
        )

    content = Div(
        Style(DOCS_CSS),
        Div(H1(_("docs.library_heading")), cls="page-header"),
        P(_("docs.library_intro"), style="margin-bottom:14px;"),
        Form(
            Input(type="search", name="q", value=q, cls="input", placeholder=_("docs.search_placeholder"),
                  style="flex:2 1 220px;"),
            Select(Option(_("docs.all_types"), value=""),
                   *[Option(type_label(_, t), value=t, selected=(t == type)) for t in TYPES],
                   name="type", cls="input", style="flex:1 1 160px;"),
            Button(_("docs.search"), type="submit", cls="btn btn-primary"),
            method="get", action="/library", style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;",
        ),
        Div(
            H3(_("docs.in_fmmt"), cls="card-title"),
            Div(*[our_item(d) for d in ours], cls="doc-list") if ours else
            P(_("docs.none_library"), style="color:var(--c-text-3);font-size:.875rem;"),
            cls="card", style="margin-bottom:16px;",
        ),
        Div(
            H3(_("docs.on_ifixit"), cls="card-title"),
            P(ifx_error, cls="alert alert-warning") if ifx_error else
            (Div(*[ifx_page(p) for p in ifx]) if ifx else
             P(_("docs.no_results") if q else _("docs.ifixit_prompt"),
               style="color:var(--c-text-3);font-size:.875rem;")),
            cls="card",
        ),
        cls="fb-page", style="max-width:860px;",
    )
    return pub_shell(content, title=_("title.library"), lang=lang)


@rt("/documents/{document_id}/file")
async def get(req, document_id: str):
    try:
        content, ctype, disposition = await docs_api.get_file(document_id)
    except Exception:
        return Response("Not found", status_code=404)
    headers = {"Content-Disposition": disposition} if disposition else {}
    return Response(content, media_type=ctype, headers=headers)


@rt("/documents/ifixit-results")
async def get(req, q: str = ""):
    """HTML fragment for the picker. Logged-in only: it exists to attach."""
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return HTMLResponse("")
    _ = make_t(req.session.get("lang", "en"))
    try:
        pages = await docs_api.search_ifixit(q)
        frag = ifixit_results(_, pages)
    except Exception:
        frag = ifixit_results(_, [], error=_("docs.ifixit_error"))
    # Serialised by hand: an FT returned from a route is wrapped in a full page.
    return HTMLResponse(to_xml(frag))


# ── actions on a device ──────────────────────────────────────────────────────

@rt("/device/{device_id}/documents/ifixit")
async def post(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    ok = await attach_selected(token, device_id, form.getlist("ifixit_doc"))
    return _back(device_id, docs="attached" if ok else "none_selected")


@rt("/device/{device_id}/documents/upload")
async def post(req, device_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    form = await req.form()
    f = form.get("file")
    content = await f.read() if f is not None and getattr(f, "filename", "") else b""
    if not content:
        return _back(device_id, docs="error")
    try:
        await docs_api.upload(token, device_id, f.filename, content,
                              (form.get("title") or "").strip(), form.get("type") or "",
                              form.get("language") or "en")
    except Exception as e:
        return _back(device_id, docs="error", docs_detail=_error_text(e))
    return _back(device_id, docs="uploaded")


@rt("/device/{device_id}/documents/{document_id}/remove")
async def post(req, device_id: str, document_id: str):
    token, redirect = auth_helper.require_auth(req)
    if redirect:
        return redirect
    try:
        await docs_api.detach(token, device_id, document_id)
    except Exception:
        return _back(device_id, docs="error")
    return _back(device_id, docs="removed")
