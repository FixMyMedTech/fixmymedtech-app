# pages/fault_list.py — the maintenance organizations' fault queue.
#
# Scoped to faults on devices my organizations MAINTAIN (not the ones they own),
# which is where a reported fault actually lands. The maintenance-org admin
# assigns it from here; everything after that happens on the fault detail page.

from fasthtml.common import *
from starlette.responses import RedirectResponse
import json
import httpx

from i18n import t as make_t

# __ API imports __
import features.auth.helper as auth_helper
import features.auth.api as auth_api
import features.faults.api as faults_api

from components import page_shell, status_badge, fmt_date
rt = APIRouter()


def _js_json(value) -> str:
    r"""json.dumps output that is safe inside a <script> element.

    JSON itself doesn't forbid '</script>', and FastHTML's Script() doesn't
    escape it either, so an HTML parser would end the block at a description
    containing that sequence. Encoding <, > and & as \u escapes keeps the JSON
    byte-identical after parsing while making that impossible.
    """
    return (json.dumps(value, ensure_ascii=False)
            .replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e"))


FT_SEARCH_JS = """
function ftSearch() {
  var input = document.getElementById('ft-search');
  var q = ((input && input.value) || '').trim().toLowerCase();
  var rows = document.querySelectorAll('tr[data-m]');
  var shown = 0;
  for (var i = 0; i < rows.length; i++) {
    var hit = !q || rows[i].getAttribute('data-m').indexOf(q) !== -1;
    rows[i].style.display = hit ? '' : 'none';
    if (hit) shown++;
  }

  var table = document.getElementById('ft-table');
  var empty = document.getElementById('ft-empty');
  if (table) table.style.display = shown ? '' : 'none';
  if (empty) empty.style.display = shown ? 'none' : '';

  var count = document.getElementById('ft-count');
  if (count) {
    count.textContent = shown + ' ' +
      (shown === 1 ? count.dataset.one : count.dataset.many) + ' ' + count.dataset.tail;
  }

  var box = document.getElementById('ft-sugg');
  if (!box) return;
  box.textContent = '';
  if (!q) { box.hidden = true; return; }

  var hits = FT_INDEX.filter(function (f) { return f.m.indexOf(q) !== -1; }).slice(0, 8);
  box.hidden = false;
  if (!hits.length) {
    var none = document.createElement('div');
    none.className = 'sugg-empty';
    none.textContent = FT_NONE;
    box.appendChild(none);
    return;
  }
  hits.forEach(function (f) {
    var a = document.createElement('a');
    a.className = 'sugg-item';
    a.href = '/device/' + encodeURIComponent(f.device_id) + '/fault/' + encodeURIComponent(f.id);
    var name = document.createElement('span');
    name.className = 'sugg-name';
    name.textContent = f.name;
    var sub = document.createElement('span');
    sub.className = 'sugg-sub';
    sub.textContent = f.sub;
    a.appendChild(name);
    a.appendChild(sub);
    box.appendChild(a);
  });
}

function ftSearchClose() {
  var box = document.getElementById('ft-sugg');
  if (box) box.hidden = true;
}

document.addEventListener('click', function (e) {
  var wrap = document.querySelector('.dev-search');
  if (wrap && !wrap.contains(e.target)) ftSearchClose();
});
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') ftSearchClose();
});
"""

# In-app assign dialog. Device and fault names come from FT_INDEX and are only
# ever assigned to textContent, so a hostile name can't reach the markup.
# The candidate list is rebuilt from FT_ORG_MEMBERS on every open, so the same
# dialog serves every fault on the page — including faults from different
# maintenance organizations.
ASSIGN_DIALOG_JS = """
function assignAsk(fid) {
  var f = FT_INDEX.filter(function (x) { return x.id === fid; })[0];
  document.getElementById('assign-name').textContent = f ? f.name : '';
  var sel = document.getElementById('assigned_to');
  var submit = document.getElementById('assign-submit');
  var form = document.getElementById('assign-dialog-form');
  var people = (f && FT_ORG_MEMBERS[f.org]) || [];

  while (sel.firstChild) sel.removeChild(sel.firstChild);
  var ph = document.createElement('option');
  ph.value = '';
  ph.textContent = FT_ASSIGN_PICK;
  sel.appendChild(ph);
  people.forEach(function (p) {
    var o = document.createElement('option');
    o.value = p.id;
    o.textContent = p.label;
    sel.appendChild(o);
  });
  sel.value = '';
  sel.disabled = people.length === 0;
  if (submit) submit.disabled = people.length === 0;
  if (f) form.setAttribute('action', '/faults/' + fid + '/assign');

  document.getElementById('assign-dialog').showModal();
}
if (window.ASSIGN_OPEN) {
  document.getElementById('assign-dialog').showModal();
}
"""


# ══════════════════════════════════════════════════════════════
# MAINTAINED FAULTS LIST
# ══════════════════════════════════════════════════════════════

@rt("/faults")
async def get(req, status: str = "", assign: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    lang = req.session.get("lang", "en")
    _ = make_t(lang)

    try:
        faults = await faults_api.list_maintained_faults(token, status or None)
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            auth_helper.clear_session(req)
            return RedirectResponse("/login?expired=1", status_code=302)
        if e.response.status_code == 403:
            return page_shell(
                Div(
                    Div("⚠", style="font-size:2rem;display:block;margin-bottom:10px;"),
                    H2(_("fault_list.access_denied")),
                    P(_("fault_list.access_msg")),
                    style="text-align:center;padding:60px 24px;"
                ),
                lang=lang
            )
        faults = []
    except Exception:
        faults = []

    try:
        me = await auth_api.get_me(token)
    except Exception:
        me = {}

    status_filters = [
        ("", _("fault_list.filter_all")),
        ("open", _("fault_list.filter_open")),
        ("assigned", _("fault_list.filter_assigned")),
        ("diagnosed", _("fault_list.filter_diagnosed")),
        ("approved", _("fault_list.filter_approved")),
        ("in_progress", _("fault_list.filter_in_progress")),
        ("resolved", _("fault_list.filter_resolved")),
    ]
    pills = [
        A(label, href=f"/faults?status={val}", cls=f"pill {'active' if status == val else ''}")
        for val, label in status_filters
    ]

    # Candidate assignees, per maintenance organization. The dialog is opened
    # client-side by assignAsk(), so the options for every organization on the
    # page have to be fetched up front — the API token lives in the session and
    # is never available to page JavaScript. One request per distinct org.
    assign_fault = next((f for f in faults if str(f.get("id")) == assign), None) if assign else None
    wanted = {}
    for f in faults:
        if not (auth_helper.can_assign_fault(me, f) and f.get("status") in ("open", "assigned")):
            continue
        device = f.get("device") or {}
        org = str(device.get("organization_maintenance_id") or "")
        if org and org not in wanted:
            wanted[org] = str(f.get("device_id"))

    people_by_org = {}
    for org, device_id in wanted.items():
        try:
            people_by_org[org] = await faults_api.get_fault_assignees(token, device_id)
        except Exception:
            people_by_org[org] = []

    def _label(a):
        return _("role." + (a.get("role") or "technician"))

    org_members = {
        org: [{"id": str(a.get("id")),
               "label": f"{a.get('full_name', '')} — {_label(a)}"} for a in people]
        for org, people in people_by_org.items()
    }

    assignees = []
    if assign_fault:
        org = str((assign_fault.get("device") or {}).get("organization_maintenance_id") or "")
        assignees = people_by_org.get(org, [])

    rows = []
    search_index = []
    for f in faults:
        device = f.get("device") or {}
        assigned = f.get("assigned_to_profile") or {}
        dev_name = device.get("name", "") or _("common.fallback")
        assigned_name = assigned.get("full_name") or ""
        sev = f.get("severity", "medium")
        st = f.get("status", "open")
        reported = fmt_date(f.get("reported_at", ""))

        match = " ".join(filter(None, [
            dev_name, device.get("location", ""), assigned_name,
            f.get("description", ""), f.get("reporter_name", ""),
        ])).lower()
        search_index.append({
            "id": str(f.get("id")),
            "device_id": str(f.get("device_id")),
            "org": str(device.get("organization_maintenance_id") or ""),
            "name": dev_name,
            "sub": " · ".join(filter(None, [reported, assigned_name])),
            "m": match,
        })

        view = A(_("fault_list.view"), href=f"/device/{f.get('device_id')}/fault/{f.get('id')}",
                  cls="btn btn-secondary btn-sm")
        assign_btn = ""
        if auth_helper.can_assign_fault(me, f) and st in ("open", "assigned"):
            assign_btn = Button(_("fault_list.assign"), type="button", cls="btn btn-primary btn-sm",
                                onclick=f"assignAsk({json.dumps(str(f.get('id')))})")

        rows.append(Tr(
            Td(
                Div(dev_name, style="font-weight:500;font-size:0.875rem;color:var(--c-text);"),
                Div(device.get("location", "") or _("common.fallback"),
                    style="font-size:0.75rem;color:var(--c-text-3);margin-top:2px;"),
            ),
            Td(status_badge(sev, "severity", lang=lang), **{"data-label": _("fault_list.col_severity")}),
            Td(status_badge(st, "fault", lang=lang), **{"data-label": _("fault_list.col_status")}),
            Td(reported, **{"data-label": _("fault_list.col_reported")}),
            Td(assigned_name or _("fault_list.unassigned"),
               **{"data-label": _("fault_list.col_assignee")}),
            Td(Div(view, assign_btn, cls="actions")),
            **{"data-m": match},
        ))

    table = Div(
        Table(
            Thead(Tr(Th(_("fault_list.col_device")), Th(_("fault_list.col_severity")),
                    Th(_("fault_list.col_status")), Th(_("fault_list.col_reported")),
                    Th(_("fault_list.col_assignee")), Th("", style="text-align:right;"))),
            Tbody(*rows) if rows else Tbody()
        ),
        id="ft-table",
        cls="table-wrap has-cards",
        style="" if rows else "display:none;",
    )

    empty_msg = Div(_("fault_list.empty"),
        id="ft-empty",
        style="text-align:center;padding:32px;color:var(--c-text-3);border:1px dashed "
              "var(--c-border);border-radius:var(--r-lg);" + ("" if not rows else "display:none;"))

    search_bar = Div(
        Input(id="ft-search", type="search", cls="input",
              placeholder=_("fault_list.search_placeholder"),
              autocomplete="off", oninput="ftSearch()",
              **{"aria-label": _("fault_list.search_placeholder")}),
        Div(id="ft-sugg", cls="dev-sugg", hidden=True),
        cls="dev-search",
    )

    role_labels = {str(a.get("id")): _label(a) for a in assignees}
    assign_dialog = Dialog(
        Form(
            H3(_("fault_list.assign_title"), style="margin:0 0 6px 0;font-size:1.05rem;"),
            P(_("fault_list.assign_msg"), " ",
              Span("", id="assign-name"),
              style="color:var(--c-text-2);font-size:0.875rem;margin:0 0 14px;"
                    "word-break:break-word;overflow-wrap:anywhere;"),
            Label(_("fault_list.assign_to"), cls="label", for_="assigned_to"),
            Select(
                Option(_("fault_list.assign_pick"), value=""),
                *[Option(f"{a.get('full_name','')} — {role_labels[str(a.get('id'))]}",
                         value=a.get("id")) for a in assignees],
                name="assigned_to", id="assigned_to", cls="input",
            ),
            Input(type="hidden", name="status", value=status),
            Div(
                Button(_("groups.cancel"), type="button", cls="btn btn-secondary",
                       onclick="document.getElementById('assign-dialog').close()"),
                Button(_("fault_list.assign"), type="submit", id="assign-submit",
                       cls="btn btn-primary",
                       disabled=True if not assignees else None),
                style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px;",
            ),
            method="post",
            action=f"/faults/{assign_fault.get('id')}/assign" if assign_fault else "/faults",
            id="assign-dialog-form",
            style="padding:20px;max-width:440px;width:90%;",
        ),
        id="assign-dialog",
        style="border:none;border-radius:12px;box-shadow:0 10px 40px rgba(0,0,0,.2);",
    )

    n = len(faults)
    one, many = _("fault_list.fault"), _("fault_list.fault") + _("fault_list.faults_plural")
    tail = _("fault_list.tail")
    count_line = P(
        Span(f"{n} {one if n == 1 else many} {tail}", id="ft-count",
             **{"data-one": one, "data-many": many, "data-tail": tail}),
        style="color:var(--c-text-3);",
    )

    page_script = Script(
        "const FT_INDEX = " + _js_json(search_index) + ";\n"
        "const FT_NONE = " + _js_json(_("fault_list.search_none")) + ";\n"
        "const FT_ORG_MEMBERS = " + _js_json(org_members) + ";\n"
        "const FT_ASSIGN_PICK = " + _js_json(_("fault_list.assign_pick")) + ";\n"
        "window.ASSIGN_OPEN = " + _js_json(bool(assign_fault)) + ";\n"
        + FT_SEARCH_JS
        + ASSIGN_DIALOG_JS
    )

    content = Div(
        Div(Div(H1(_("fault_list.title")), count_line), cls="page-header"),
        Div(*pills, cls="toolbar"),
        search_bar,
        table,
        empty_msg,
        assign_dialog,
        page_script,
    )

    return page_shell(content, current="/faults", title=_("title.fault_list"), lang=lang)


@rt("/faults/{fault_id}/assign")
async def post_assign(req, fault_id: str, assigned_to: str = "", status: str = ""):
    token, redirect = auth_helper.require_auth(req)
    if redirect: return redirect

    if assigned_to:
        try:
            await faults_api.assign_fault(token, fault_id, assigned_to)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                auth_helper.clear_session(req)
                return RedirectResponse("/login?expired=1", status_code=302)

    q = f"?status={status}" if status else ""
    return RedirectResponse(f"/faults{q}", status_code=303)
