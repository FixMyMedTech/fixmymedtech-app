# components.py — document list, iFixit picker and upload form, shared by the
# device page, device registration and the public QR page.

from fasthtml.common import *

TYPES = ("user_manual", "service_manual", "quick_guide", "diagram", "general_guide")
TYPE_ICONS = {"user_manual": "📘", "service_manual": "🔧", "quick_guide": "📋",
              "diagram": "📐", "general_guide": "📄"}
LANGS = ("en", "es", "fr", "pt", "de", "it", "other")

DOCS_CSS = """
.doc-list { display:flex; flex-direction:column; gap:8px; }
.doc-item { display:flex; align-items:center; gap:12px; padding:10px 12px; border:1px solid var(--c-border);
  border-radius:var(--r-md); background:var(--c-surface); }
.doc-item:hover { border-color:var(--c-primary); }
.doc-ico { font-size:1.25rem; flex-shrink:0; width:28px; text-align:center; }
.doc-body { flex:1; min-width:0; }
.doc-title { font-weight:500; font-size:.875rem; color:var(--c-text); overflow-wrap:anywhere; }
.doc-meta { font-size:.75rem; color:var(--c-text-3); margin-top:2px; }
.doc-src { display:inline-block; font-size:.68rem; font-weight:600; padding:1px 7px; border-radius:9999px;
  background:var(--c-bg-2); color:var(--c-text-2); margin-left:4px; }
.doc-src.ifixit { background:var(--c-blue-lt); color:var(--c-blue); }
.ifx-page { margin-top:12px; }
.ifx-page-title { font-weight:600; font-size:.85rem; margin-bottom:6px; }
.ifx-doc { display:flex; align-items:flex-start; gap:8px; padding:6px 0; font-size:.85rem; cursor:pointer; }
.ifx-doc input { margin-top:3px; }
.doc-form-row { display:grid; grid-template-columns:2fr 1fr 1fr; gap:10px; }
@media (max-width: 640px) { .doc-form-row { grid-template-columns:1fr; } }
"""


def type_label(_, t: str) -> str:
    return _(f"docs.type_{t}") if t in TYPES else _("docs.type_general_guide")


def _meta(_, d: dict) -> list:
    bits = [type_label(_, d.get("type"))]
    if d.get("pages"):
        bits.append(f"{d['pages']} {_('docs.pages')}")
    if d.get("language") and d["language"] != "other":
        bits.append(d["language"].upper())
    return bits


def doc_item(_, d: dict, remove_action: str = ""):
    src = d.get("source")
    return Div(
        Span(TYPE_ICONS.get(d.get("type"), "📄"), cls="doc-ico"),
        Div(
            A(d.get("title", ""), href=d.get("url") or "#", target="_blank", rel="noopener",
              cls="doc-title"),
            Div(" · ".join(_meta(_, d)),
                Span(_("docs.source_ifixit") if src == "ifixit" else _("docs.source_upload"),
                     cls=f"doc-src {'ifixit' if src == 'ifixit' else ''}"),
                cls="doc-meta"),
            cls="doc-body",
        ),
        Form(Button(_("docs.remove"), type="submit", cls="btn btn-secondary btn-sm"),
             method="post", action=remove_action) if remove_action else "",
        cls="doc-item",
    )


def doc_list(_, docs: list, device_id: str = "", can_remove: bool = False):
    if not docs:
        return P(_("docs.none"), style="color:var(--c-text-3);font-size:.875rem;")
    return Div(*[doc_item(_, d, f"/device/{device_id}/documents/{d['id']}/remove" if can_remove else "")
                 for d in docs], cls="doc-list")


def ifixit_results(_, pages: list, error: str = ""):
    """The checkbox list the picker loads. Values are "<documentid>|<page>"."""
    if error:
        return P(error, cls="alert alert-warning")
    if not pages:
        return P(_("docs.no_results"), style="color:var(--c-text-3);font-size:.875rem;")
    return Div(*[
        Div(
            Div(A(p["title"], href=p["url"], target="_blank", rel="noopener"), cls="ifx-page-title"),
            *[Label(
                Input(type="checkbox", name="ifixit_doc", value=f"{d['ifixit_document_id']}|{p['title']}"),
                Span(TYPE_ICONS.get(d["type"], "📄"), " ", d["title"],
                     Span(" · " + " · ".join(_meta(_, d)), style="color:var(--c-text-3);")),
                cls="ifx-doc",
              ) for d in p["documents"]],
            cls="ifx-page",
        ) for p in pages
    ])


PICKER_JS = """
function ifxSearch(btn){
  var box = btn.closest('.ifx-picker');
  var input = box.querySelector('.ifx-q');
  if (!input.value.trim()) {
    // Registration: start from what was typed in the form.
    var parts = [];
    ['manufacturer', 'model'].forEach(function(id){
      var el = document.getElementById(id);
      if (el && el.value.trim()) parts.push(el.value.trim());
    });
    input.value = parts.join(' ');
  }
  var out = box.querySelector('.ifx-results');
  if (!input.value.trim()) { input.focus(); return; }
  out.textContent = box.dataset.searching;
  fetch('/documents/ifixit-results?q=' + encodeURIComponent(input.value.trim()), {credentials: 'same-origin'})
    .then(function(r){ return r.text(); })
    .then(function(html){ out.innerHTML = html; })
    .catch(function(){ out.textContent = box.dataset.error; });
}
function ifxKey(e){ if (e.key === 'Enter') { e.preventDefault(); ifxSearch(e.target); } }
"""


def ifixit_picker(_, query: str = "", submit_label: str = ""):
    """Search box + results. Put it inside a form: ticked documents are sent
    as ifixit_doc values. ``submit_label`` adds a submit button."""
    return Div(
        P(_("docs.find_hint"), style="font-size:.85rem;margin-bottom:10px;"),
        Div(
            Input(type="search", cls="input ifx-q", value=query, placeholder=_("docs.search_placeholder"),
                  onkeydown="ifxKey(event)"),
            Button(_("docs.search"), type="button", cls="btn btn-secondary", onclick="ifxSearch(this)"),
            style="display:flex;gap:8px;",
        ),
        Div(cls="ifx-results", style="margin-top:6px;"),
        Button(submit_label, type="submit", cls="btn btn-primary", style="margin-top:12px;") if submit_label else "",
        Script(PICKER_JS),
        cls="ifx-picker", data_searching=_("docs.searching"), data_error=_("docs.ifixit_error"),
    )


def upload_form(_, device_id: str, lang: str):
    return Form(
        P(_("docs.upload_hint"), style="font-size:.85rem;margin-bottom:10px;"),
        Div(
            Div(Label(_("docs.title_label"), cls="label"),
                Input(name="title", cls="input", required=True, maxlength="200"), cls="form-group"),
            Div(Label(_("docs.type_label"), cls="label"),
                Select(*[Option(type_label(_, t), value=t) for t in TYPES], name="type", cls="input"),
                cls="form-group"),
            Div(Label(_("docs.language_label"), cls="label"),
                Select(*[Option(_(f"docs.lang_{l}"), value=l, selected=(l == lang)) for l in LANGS],
                       name="language", cls="input"),
                cls="form-group"),
            cls="doc-form-row",
        ),
        Div(Label(_("docs.file_label"), cls="label"),
            Input(type="file", name="file", accept="application/pdf,.pdf", required=True, cls="input"),
            cls="form-group"),
        Button(_("docs.upload"), type="submit", cls="btn btn-primary"),
        method="post", action=f"/device/{device_id}/documents/upload", enctype="multipart/form-data",
    )
